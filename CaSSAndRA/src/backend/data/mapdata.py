import logging
logger = logging.getLogger(__name__)

import base64
import re
import io
import os
import json
import pandas as pd
import math
import networkx as nx
from dataclasses import dataclass, field, asdict
from shapely.geometry import *
from PIL import Image

from .roverdata import robot
from .cfgdata import PathPlannerCfg, pathplannercfg, rovercfg
from .. map import map

@dataclass
class Perimeter:
    name: str = ''
    angle_offset: int = 0
    perimeter: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    perimeter_polygon: Polygon = Polygon()
    selected_perimeter: Polygon = Polygon()
    perimeter_for_plot: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    perimeter_points: MultiPoint = MultiPoint()
    search_wire: LineString = LineString()
    search_wire_points: MultiPoint = MultiPoint()
    gotopoints: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    gotopoint: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    mowpath: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    preview: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    obstacles: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    obstacle_img: Image = field(default_factory = lambda: 
                                Image.open(os.path.dirname(__file__).replace('/backend/data', '/assets/icons/obstacle.png')))
    astar_graph: nx.Graph = nx.Graph()
    areatomow: float = 0
    distancetogo: float = 0
    map_crc: int = None
    current_perimeter_file: str = ''
    plotgotopoints: bool = False
    # Progress bar
    calculating: bool = False
    calculated_progress: int = 0
    total_progress: int = 0
    task_progress: int = 0
    total_tasks: int = 0

    def set_gotopoint(self, clickdata: dict) -> None:
        goto = {'X':[clickdata['points'][0]['x']], 'Y':[clickdata['points'][0]['y']], 'type': ['way']}
        self.gotopoint = pd.DataFrame(goto)

    def create_perimeter_polygon(self) -> None:
        df = self.perimeter
        perimeter = df[df['type'] == 'perimeter']
        search_wire = df[df['type'] == 'search wire']
        df = df[df['type'] != 'perimeter']
        df = df[df['type'] != 'way']
        df = df[df['type'] != 'dockpoints']
        df = df[df['type'] != 'search wire']
        perimeter_coords = perimeter[['X', 'Y']]
        #create perimeter
        perimeter = Polygon(perimeter_coords.values.tolist())
        #create exclusions
        for exclusion in pd.unique(df['type']):
            exclusions = df[df['type'] == exclusion]
            exclusion_coords = exclusions[['X', 'Y']]
            exclusions = Polygon(exclusion_coords.values.tolist())
            if exclusions.is_valid:
                perimeter = perimeter.difference(exclusions)
            else:
                perimeter = perimeter.difference(exclusions.convex_hull)
        self.perimeter_polygon = perimeter
        #create search wire
        if not search_wire.empty and len(search_wire) >= 2:
            search_wire_coords = search_wire[['X', 'Y']]
            self.search_wire = LineString(search_wire_coords.values.tolist())
    
    def create_perimeter_for_plot(self) -> None:
        self.perimeter_for_plot = pd.DataFrame()
        perimeter = self.perimeter
        #Add first value to the end, if perimeter or exclusion
        types = perimeter['type'].unique()
        for type in types:
            if type != 'dockpoints' and type != 'search wire':
                coords = perimeter[perimeter['type'] == type]
                first_value_cpy = coords.iloc[:1,:]
                coords = pd.concat([coords, first_value_cpy], ignore_index=True)
                self.perimeter_for_plot = pd.concat([self.perimeter_for_plot, coords], ignore_index=True)
            elif type == 'dockpoints':
                coords = perimeter[perimeter['type'] == type]
                self.perimeter_for_plot = pd.concat([self.perimeter_for_plot, coords], ignore_index=True)
    
    def create_points_from_polygon(self) -> None:
        #Create MultiPoint from polygon (perimeter and exclusions)
        perimeter_coords = list(self.perimeter_polygon.exterior.coords)
        for excl in self.perimeter_polygon.interiors:
            excl_coords = list(excl.coords)
            perimeter_coords.extend(excl_coords)
        perimeter_points = MultiPoint((perimeter_coords))
        self.perimeter_points = perimeter_points
        #Create MultiPoint from search wire
        if not self.search_wire.is_empty:
            search_wire_coords = list(self.search_wire.coords)
            search_wire_points = MultiPoint(search_wire_coords)
            self.search_wire_points = search_wire_points
    
    def create_go_to_points(self) -> None:
        perimeter = self.perimeter_polygon
        bounds = perimeter.bounds
        offsx = bounds[0]
        offsy = bounds[1]
        mask_coordsx = []
        mask_coordsy = []
        mask_coordsx.append(((bounds[0], bounds[1]-10),(bounds[0], bounds[3]+10)))
        mask_coordsy.append(((bounds[0]-10, bounds[1]),(bounds[2]+10, bounds[1])))
        while True:
            offsx = offsx + 0.5
            offsy = offsy + 0.5
            if offsy > bounds[3] and offsx > bounds[2]:
                break
            mask_coordsx.append(((offsx, bounds[1]-10),(offsx, bounds[3]+10)))
            mask_coordsy.append(((bounds[0]-10, offsy),(bounds[2]+10, offsy)))
        linemaskx = MultiLineString(mask_coordsx)
        linemasky = MultiLineString(mask_coordsy)
        points = linemaskx.intersection(linemasky)
        points = points.intersection(perimeter)
        gotopoints = pd.DataFrame(columns=['X', 'Y', 'type'])
        for point in points.geoms:
            coords_df = pd.DataFrame(point.coords)
            coords_df.columns = ['X','Y']
            coords_df['type'] = 'possible gotos'
            gotopoints = pd.concat([gotopoints, coords_df], ignore_index=True)
            self.gotopoints = gotopoints

    def create_networkx_graph(self):
        G = nx.Graph()
        #Create networkx edges for perimeter
        logger.info('Create networkx edges for perimeter (A* pathfinder)')
        perimeter_coords = list(self.perimeter_polygon.exterior.coords)
        for i in range(len(perimeter_coords)-1):
            line = LineString(([perimeter_coords[i], perimeter_coords[i+1]]))
            G.add_edge(list(line.coords)[0], list(line.coords)[1], weight=line.length)
        logger.debug('NetworkX perimeter edges: '+str(len(G.edges)))
        
        #Create networkx edges for exclusions
        logger.info('Create networkx edges for exclusions (A* pathfinder)')
        for excl in self.perimeter_polygon.interiors:
            excl_coords = list(excl.coords)
            for i in range(len(excl_coords)-1):
                line = LineString(([excl_coords[i], excl_coords[i+1]]))
                G.add_edge(list(line.coords)[0], list(line.coords)[1], weight=line.length)
        logger.debug('NetworkX perimeter + exlusion edges: '+str(len(G.edges)))

        #Create networkx edges betweed exclusions and perimeter
        logger.info('Create networkx edges between exclusions and perimeter (A* pathfinder)')
        for excl in self.perimeter_polygon.interiors:
            connected_to_perimeter = False
            excl_coords = list(excl.coords)
            for i in range(len(excl_coords)-1):
                for k in range(len(perimeter_coords)-1):
                    possible_way = self.check_direct_way(excl_coords[i], perimeter_coords[k])
                    if possible_way:
                        connected_to_perimeter = True
                        direct_way = LineString((excl_coords[i], perimeter_coords[k]))
                        G.add_edge(list(direct_way.coords)[0], list(direct_way.coords)[1], weight=direct_way.length)
            if connected_to_perimeter == False:
                logger.info('One exclusion could not be connected to perimeter')
                logger.info('Trying to connect to other exclusions')
                for l in range(len(excl_coords)-1):
                    for other_exclusion in self.perimeter_polygon.interiors:
                        other_exclusion_coords = list(other_exclusion.coords)
                        for m in range(len(other_exclusion.coords)):
                            possible_way = self.check_direct_way(excl_coords[l], other_exclusion_coords[m])
                            if possible_way:
                                connected_to_perimeter = True
                                direct_way = LineString((excl_coords[l], other_exclusion_coords[m]))
                                G.add_edge(list(direct_way.coords)[0], list(direct_way.coords)[1], weight=direct_way.length)
        logger.debug('NetworkX perimeter + exclusion + perimeter/exclusion edges: '+str(len(G.edges)))
        #Create networkx edges from search wire
        logger.info('Create networkx edges for search wire (A* pathfinder)')
        if not self.search_wire.is_empty:
            search_wire_coords = list(self.search_wire.coords)
            for i in range(len(search_wire_coords)-1):
                line = LineString(([search_wire_coords[i], search_wire_coords[i+1]]))
                G.add_edge(list(line.coords)[0], list(line.coords)[1], weight=line.length/2)
                for other_search_wire_point in self.search_wire_points.geoms:
                    possible_way = self.check_direct_way(search_wire_coords[i], list(other_search_wire_point.coords)[0])
                    if possible_way:
                        direct_way = LineString((search_wire_coords[i], list(other_search_wire_point.coords)[0]))
                        G.add_edge(list(direct_way.coords)[0], list(direct_way.coords)[1], weight=direct_way.length/2)
                for perimeter_point in self.perimeter_points.geoms:
                    possible_way = self.check_direct_way(search_wire_coords[i], list(perimeter_point.coords)[0])
                    if possible_way:
                        direct_way = LineString((search_wire_coords[i], list(perimeter_point.coords)[0]))
                        G.add_edge(list(direct_way.coords)[0], list(direct_way.coords)[1], weight=direct_way.length)
            logger.debug('NetworkX perimeter + exclusion + perimeter/exclusion edges + search wire edges: '+str(len(G.edges)))
        else:
            logger.info('No search wire found.')
        self.astar_graph = G
    
    def check_direct_way(self, start, end) -> bool:
        way = LineString([start, end])
        direct_way_possible = way.within(self.perimeter_polygon)
        return direct_way_possible
    
    def create(self, name: str) -> None:
        self.name = name
        self.preview = pd.DataFrame()
        self.mowpath = pd.DataFrame()
        self.obstacles = pd.DataFrame()
        self.create_perimeter_polygon()
        self.create_perimeter_for_plot()
        self.create_points_from_polygon()
        self.create_go_to_points()
        self.create_networkx_graph()
        self.save_map_name()
    
    def calc_route_preview(self, route: list) -> None:
        self.preview = pd.DataFrame(route)
        self.preview.columns = ['X', 'Y']
        self.preview['type'] = 'preview route'
    
    def read_map_name(self) -> str:
        try:
            with open(self.current_perimeter_file) as f: 
                tmp_data = json.load(f)
                f.close()
                return tmp_data['PERIMETERNAME']
        except Exception as e:
            logger.error('Backend: Could not read data from file. Missing tmp.json')
            logger.debug(str(e))
            return ''
    
    def save_map_name(self) -> None:
        tmp_data = {'PERIMETERNAME': self.name}
        try:
            with open(self.current_perimeter_file, 'w') as f:
                json.dump(tmp_data, f, indent=4)
            logger.info('Backend: Perimeter name is successfully saved in tmp.json')
        except Exception as e:
            logger.error('Backend: Could not saved perimeter name to tmp.json')
            logger.debug(str(e))
    
    def clear_map(self) -> None:
        self.name = ''
        self.perimeter = pd.DataFrame()
        self.preview = pd.DataFrame()
        self.mowpath = pd.DataFrame()
        self.perimeter_polygon = Polygon()
        self.perimeter_for_plot = pd.DataFrame()
        self.gotopoints = pd.DataFrame()
        self.gotopoint = pd.DataFrame()
        self.areatomow = 0
        self.distancetogo = 0
        self.map_crc = None
        self.save_map_name()

@dataclass
class Perimeters:
    selected: str = ''
    map_old_name: str = None
    imported: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    selected_import: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    saved: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    selected_save: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    selected_point: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    selected_name: str = ''
    build: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    build_cpy: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    legacy_figure: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    dockpoints: pd.DataFrame = field(default_factory = lambda: pd.DataFrame(columns=['X', 'Y']))
    import_status: int = -1   
    select_imported_status: int = -1  

    def init(self) -> None:
        self.selected = ''
        self.map_old_name = None
        self.selected_save = pd.DataFrame()
        self.selected_point = pd.DataFrame()
        self.selected_name = ''
        self.build = pd.DataFrame()
        self.build_cpy = pd.DataFrame()
        self.dockpoints = pd.DataFrame(columns=['X', 'Y'])

    def import_sunray(self, content: str) -> None:
        coords_all = pd.DataFrame()
        content_type, content = content.split(',')
        decoded = base64.b64decode(content)
        try:
            df = pd.read_json(io.StringIO(decoded.decode('utf-8')))
        except Exception as e:
            logger.warning('Backend: Import of sunray file failed')
            logger.debug(str(e))
            self.imported = pd.DataFrame()
            self.import_status = -1
            return
        try:
            for map_number in range(len(df)): 
                if not df[df.index == map_number].isnull().values.any():
                    coords = pd.DataFrame(df['perimeter'][map_number])
                    coords['type'] = 'perimeter'
                    if not coords.empty:  
                        try:
                            coords_exclusions = df['exclusions'][map_number]
                            for i, exclusion in enumerate(coords_exclusions):
                                exclusion_df = pd.DataFrame(exclusion)
                                if len(exclusion_df) > 3:
                                    exclusion_df['type'] = 'exclusion_'+str(i)
                                    coords = pd.concat([coords, exclusion_df], ignore_index=True)
                        except:
                            logger.info('Backend: No exclusions found in sunray file')
                        try: 
                            dockpoints_df = pd.DataFrame(df['dockpoints'][map_number])
                            dockpoints_df['type'] = 'dockpoints'
                            coords = pd.concat([coords, dockpoints_df], ignore_index=True)
                        except:
                            logger.info('Backend: No dockpoints found in sunray file')
                        coords = coords.drop(['delta', 'timestamp'], axis=1)
                        #Handle some sunray exports without sol Axis
                        try:
                            coords = coords.drop(['sol'], axis=1)
                        except Exception as e:
                            logger.info('Backend: Sunray file has no sol Axis')
                            logger.debug(str(e))
                        coords['map_nr'] = map_number
                        coords_all = pd.concat([coords_all, coords], ignore_index=True)
            self.import_status = 0
            self.imported = coords_all
            return
    
        except Exception as e:
            logger.warning('Backend: Sunray file import failed')
            logger.debug(str(e))
            self.imported = -1
            self.imported = pd.DataFrame()
            return
    
    def create_perimeter_for_plot(self, data_to_plot: pd.DataFrame) -> pd.DataFrame:
        perimeter_df = pd.DataFrame()
        #Add first value to the end, if perimeter or exclusion
        types = data_to_plot['type'].unique()
        for type in types:
            if type == 'dockpoints' or type == 'search wire':
                coords = data_to_plot[data_to_plot['type'] == type]
                perimeter_df = pd.concat([perimeter_df, coords], ignore_index=True)
            elif type == 'edit' and (mapping_maps.selected_name == 'dockpoints' or mapping_maps.selected_name == 'search wire'):
                coords = data_to_plot[data_to_plot['type'] == type]
                perimeter_df = pd.concat([perimeter_df, coords], ignore_index=True)
            else:
                coords = data_to_plot[data_to_plot['type'] == type]
                first_value_cpy = coords.iloc[:1,:]
                coords = pd.concat([coords, first_value_cpy], ignore_index=True)
                perimeter_df = pd.concat([perimeter_df, coords], ignore_index=True)
        return perimeter_df
    
    # def export_geojson(self) -> None:
    #     if not self.perimeter_for_plot.empty:
    #         geojson = dict(type="FeatureCollection", features=[])
    #         #perimeter
    #         abs_coords = self.coords_rel_to_abs(self.perimeter_for_plot[self.perimeter_for_plot['type'] == 'perimeter'])
    #         value = dict(type="Feature", properties=dict(name="perimeter"), geometry=dict(dict(type="Polygon", coordinates=[abs_coords[['lon', 'lat']].values.tolist()])))
    #         geojson['features'].append(value)
    #         #dockpoints
    #         abs_coords = self.coords_rel_to_abs(self.perimeter_for_plot[self.perimeter_for_plot['type'] == 'dockpoints'])
    #         value = dict(type="Feature", properties=dict(name="dockpoints"), geometry=dict(dict(type="LineString", coordinates=abs_coords[['lon', 'lat']].values.tolist())))
    #         geojson['features'].append(value)
    #         #exclusions
    #         filtered = self.perimeter_for_plot[(self.perimeter_for_plot['type'] != 'perimeter') & (self.perimeter_for_plot['type'] != 'dockpoints')]
    #         for i, exclusion in enumerate(filtered['type'].unique()):
    #             abs_coords = self.coords_rel_to_abs(self.perimeter_for_plot[self.perimeter_for_plot['type'] == exclusion])
    #             value = dict(type="Feature", properties=dict(name="exclusion"), idx=i, geometry=dict(dict(type="Polygon", coordinates=[abs_coords[['lon', 'lat']].values.tolist()])))
    #             geojson['features'].append(value)
    #         res = json.dumps(geojson)
    
    def coords_rel_to_abs(self, coords: pd.DataFrame) -> pd.DataFrame:
        lat = coords[['Y']]/111111+rovercfg.lat
        lon = coords[['X']]/(111111*math.cos(math.radians(rovercfg.lat)))+rovercfg.lon 
        abs_coords = pd.DataFrame()
        abs_coords['lon'] = lon
        abs_coords['lat'] = lat
        return abs_coords
        
    def select_imported(self, nr: int) -> None:
        logger.info('Backend: Changing perimeter to nr: '+str(nr))
        try:
            perimeter = self.imported[self.imported['map_nr'] == nr]
            perimeter = perimeter.reset_index(drop=True)
            self.selected_import = perimeter
            self.select_imported_status = 0
            return
        except Exception as e:
            logger.warning('Backend: Could not change perimeter')
            logger.debug(str(e))
            self.selected_import = pd.DataFrame()
            self.select_imported_status = -1
            return
    
    def select_saved(self, perimeter: pd.DataFrame) -> None:
        self.selected_save = perimeter
        self.build = perimeter
        self.build_cpy = perimeter
        self.dockpoints = self.build[self.build['type'] == 'dockpoints']

    def add_point(self, create: str) -> None:
        try:
            if not self.build.empty and not self.build[self.build['type'] == 'edit'].empty:
                logger.debug('Add point to existing figure')
                line = LineString(self.build[self.build['type'] == 'edit'][['X', 'Y']])
                point = Point(self.selected_point[['X', 'Y']])
                line_coords = list(line.coords)
                point_coords = list(point.coords)
                ###Remove double values###
                line_coords = list(dict.fromkeys(line_coords))
                ###Look for shortest way from selected point###
                first_coords = [min(line_coords, key=lambda coord: (coord[0]-point_coords[0][0])**2 + (coord[1]-point_coords[0][1])**2)]
                first_coords_nr = line_coords.index(first_coords[0])
                if first_coords_nr <= (len(line_coords)-2):
                    second_coords = line_coords[first_coords_nr + 1]
                else:
                    second_coords = line_coords[0]
                new_line = LineString([first_coords[0], second_coords])
                new_point = new_line.interpolate(new_line.length/2)
                logger.debug('New point coordinates: '+str(list(new_point.coords)))
                new_coords = line_coords[:first_coords_nr+1]
                new_coords.extend(list(new_point.coords))
                new_coords = new_coords + line_coords[first_coords_nr+1:]
                x, y = zip(*new_coords)
                self.build = self.build[self.build['type'] != 'edit']
                new_edit = {'X': x, 'Y': y}
                new_edit = pd.DataFrame(new_edit)
                if self.selected_name == 'dockpoints':
                    self.dockpoints = new_edit
                new_edit['type'] = 'edit'
                self.build = pd.concat([self.build, new_edit], ignore_index=True)
            else:
                logger.debug('Add point: '+str(robot.position_x)+' '+str(robot.position_y))
                #remove unfinished figure
                if create != 'figure' and not self.build.empty:
                    logger.debug('Mapping remove unfinished figure')
                    self.build = self.build[self.build['type'] != 'figure']
                #create point and add to data frame
                point = {'X': [robot.position_x], 'Y': [robot.position_y], 'type': [create]}
                df = pd.DataFrame(point)
                logger.debug('Moved data to data frame: '+str(point))
                df.columns = ['X', 'Y', 'type']
                self.build = pd.concat([self.build, df], ignore_index=True)
        except Exception as e:
            logger.error('Backend: Add point not possible')
            logger.debug(str(e))
        
    def remove_point(self, create: str) -> None:
        try: 
            logger.debug('Removing point')
            figure = self.build[self.build['type'] == create]
            if figure.empty:
                logger.debug('Target existing figure')
                figure = self.build[self.build['type'] == 'edit']
                create = 'edit'
            else:
                logger.debug('Target new figure')
                self.build = self.build[self.build['type'] != create]
            if not figure.empty and (create == 'figure' or create == 'dockpoints' or create == 'search wire'):
                logger.debug('Removing last point')
                figure = figure[:-1]
                self.build = pd.concat([self.build, figure], ignore_index=True)
            elif not figure.empty and create == 'edit' and not self.selected_point.empty:
                logger.debug('Removing marked point')
                self.build = self.build.drop([self.selected_point.index[0]])
                self.build = self.build.reset_index(drop=True)
                if len(self.build[self.build['type'] == 'edit']) <= 2 and self.selected_name != 'dockpoints':
                    logger.debug('Figure has less then 3 points and will be removed')
                    self.build = self.build[self.build['type'] != 'edit']
                else:
                    self.build.loc[:,'type'] = mapping_maps.build['type'].replace(['edit'], self.selected_name)
                self.selected_point = pd.DataFrame()
                self.figure_action('recreate')
                if self.selected_name == 'dockpoints':
                    self.dockpoints = self.build[self.build['type'] == 'dockpoints']
        except Exception as e:
            logger.error('Backend: Remove point not possible')
            logger.debug(str(e))
    
    def add_figure(self, selection: dict) -> None:
        try: 
            #remove unfinished figure
            if not self.build.empty:
                self.build = self.build[self.build['type'] != 'figure']
                logger.debug('Mapping remove unfinished figure')
            if selection == None:
                logger.debug('Mapping no selection detected, break')
                return
            elif 'range' in selection:
                logger.debug('Mapping selection box detected. Create an new figure with box select.') 
                selection = selection['range']
                points = {'X': [selection['x'][0], selection['x'][1], selection['x'][1], selection['x'][0]],
                        'Y': [selection['y'][0], selection['y'][0], selection['y'][1], selection['y'][1]]}
                df = pd.DataFrame(points)
                df['type'] = 'figure'
                self.build = pd.concat([self.build, df], ignore_index=True)
            elif 'lassoPoints' in selection:
                logger.debug('Mapping selection lasso detected. Create a new figure with lasso select.')
                logger.debug('Lasso points: '+str(selection))
                selection = selection['lassoPoints']
                selection_list = list(zip(selection['x'], selection['y']))
                df = pd.DataFrame(selection_list)
                df.columns = ['X', 'Y']
                df['type'] = 'figure'
                self.build = pd.concat([self.build, df], ignore_index=True)
            else:
                logger.warning('Backend: Selection in mapping is an unknown figure')
        except Exception as e:
            logger.error('Backend: Add a figure not possible')
            logger.debug(str(e))

    def figure_action(self, action: str) -> None:
        self.selected_point = pd.DataFrame()
        try:
            logger.debug('Mapping finish figure as: '+action)
            if action == 'add' or action == 'diff':
                df = self.build[self.build['type'] == 'figure']
                df.loc[:,'type'] = 'perimeter'
                new_perimeter = map.create(df)
                if new_perimeter.geom_type != 'Polygon' or not new_perimeter.is_valid:
                    logger.info('Backend: New figure is not a polygon or not valid polygon, try again')
                    self.build = self.build[self.build['type'] != 'figure']
                    return
                logger.debug('Mapping figure coords: '+str(new_perimeter.exterior.coords))
                df = self.build[self.build['type'] != 'figure']
                old_perimeter = map.create(df)
                if action == 'add':
                    new_perimeter = old_perimeter.union(new_perimeter)
                    if new_perimeter.geom_type != 'Polygon':
                        logger.warning('Backend: Could not create new perimeter, new figure is: '+new_perimeter.geom_type)
                        new_perimeter = old_perimeter
                elif action == 'diff':
                    new_perimeter = old_perimeter.difference(new_perimeter)
                    if new_perimeter.geom_type != 'Polygon':
                        logger.warning('Backend: Could not create new perimeter, new figure is: '+new_perimeter.geom_type)
                        new_perimeter = old_perimeter
            else:
                df = self.build[self.build['type'] != 'figure']
                old_perimeter = map.create(df)
                new_perimeter = old_perimeter
                if new_perimeter.geom_type != 'Polygon':
                    logger.warning('Backend: Could not create new perimeter, new figure is: '+new_perimeter.geom_type)
            logger.debug('Mapping new perimeter is empty: '+str(new_perimeter.is_empty))
            new_perimeter = new_perimeter.simplify(0.02)
            if new_perimeter.is_empty or not new_perimeter.is_valid:
                logger.warning('Backend: Action aborted')
                self.build = self.build_cpy
                return
            else:
                logger.debug('Mapping create a new data frame')
                dockpoints = self.build[self.build['type'] == 'dockpoints']
                searchwire = self.build[self.build['type'] == 'search wire']
                self.build = pd.DataFrame(list(new_perimeter.exterior.coords))
                self.build.columns = ['X', 'Y']
                self.build['type'] = 'perimeter'
                for i, exclusion in enumerate(new_perimeter.interiors):
                    exclusion_df = pd.DataFrame(list(new_perimeter.interiors[i].coords))
                    exclusion_df.columns = ['X', 'Y']
                    exclusion_df['type'] = 'exclusion_'+str(i)
                    self.build = pd.concat([self.build, exclusion_df], ignore_index=True)
                if not dockpoints.empty:
                    self.build = pd.concat([self.build, dockpoints], ignore_index=True)
                if not searchwire.empty:
                    self.build = pd.concat([self.build, searchwire], ignore_index=True)
        except Exception as e:
            self.build = self.build_cpy
            logger.error('Backend: Create new perimeter is not possible. Exception occured. Action aborted')
            logger.debug(str(e))

    def is_changed(self) -> bool:
        try: 
            if self.build.empty:
                return True
            elif self.build[self.build['type'] == 'perimeter'].empty:
                return True
            else:
                df1 = self.build[self.build['type']!='figure']
                try:
                    df1 = df1.drop(columns=['map_nr', 'name'])
                except:
                    pass
                df2 = self.selected_save
                try:
                    df2 = df2.drop(columns=['map_nr', 'name'])
                except:
                    pass
                equal = df1.equals(df2)
                return equal
        except Exception as e:
            logger.error('Backend: Check saved and build map not possible')
            logger.debug(str(e))
            return False
    
    def check_dockpoints(self) -> None:
        try:
            old_dockpoints = self.dockpoints
            old_dockpoints = old_dockpoints[['X', 'Y']]
            old_dockpoints = old_dockpoints.reset_index(drop=True)
            if not self.build.empty:
                new_dockpoints = self.build[self.build['type'] == 'dockpoints']
                new_dockpoints = new_dockpoints[['X', 'Y']]
                new_dockpoints = new_dockpoints.reset_index(drop=True)
                equal = old_dockpoints.equals(new_dockpoints)
                if equal:
                    logger.debug('Mapping dockpoints are not changed, adjustment not neccessary')
                else:
                    dockpoints = self.build[self.build['type'] == 'dockpoints']
                    if len(dockpoints) < 2:
                        logger.debug('Mapping dockpoints are changed, but contains only one coordinate, adjustment not possible')
                    else:
                        coord = dockpoints.iloc[-1]
                        last_coord = [coord['X'], coord['Y']]
                        coord = dockpoints.iloc[-2]
                        before_last_coord = [coord['X'], coord['Y']]
                        last_vector = [last_coord[0]-before_last_coord[0], last_coord[1]-before_last_coord[1]]
                        last_vector_angle = math.atan2(last_vector[1], last_vector[0])
                        new_vector = [math.cos(last_vector_angle)*0.2, math.sin(last_vector_angle)*0.2]
                        new_last_coord = [last_coord[0]+new_vector[0], last_coord[1]+new_vector[1]]
                        self.build.iloc[-1, self.build.columns.get_loc('X')] = new_last_coord[0]
                        self.build.iloc[-1, self.build.columns.get_loc('Y')] = new_last_coord[1]
                        logger.debug('Mapping dockpoints are changed, the lastpoint is adjusted. Old values: '+str(last_coord)+' New values: '+str(new_last_coord))
            else:
                logger.debug('Mapping new map is an empty dataframe, dockpoints are not changed, adjustment not neccessary')
        except Exception as e:
            logger.error('Backend: Dockpoints adjustment not possible')
            logger.debug(str(e)) 
    
    def csvtocartesian(self, closedpath: str) -> list:
        path = re.split('[a-zA-Z]', closedpath)
        path = [point for point in path if point]
        x = []
        y = []
        for point_str in path:
            point_str_splitted = point_str.split(',')
            points_float = [float(point) for point in point_str_splitted]
            x.append(points_float[0])
            y.append(points_float[1])
        df = pd.DataFrame({'X':x, 'Y':y})
        return df
    
    def cartesiantocsv(self, coords: list, geometry_type: str) -> str:
        path = 'M'
        for i, coord in enumerate(coords):
            path = path+str(coord[0])+','+str(coord[1])+'L'
        if geometry_type != 'dockpoints' and geometry_type != 'search wire':
            path = path[:-1] + 'Z'
        else:
            path = path[:-1]
        return path

@dataclass
class Task:
    name: str = ''
    map_name: str = ''
    selected_perimeter: Polygon = Polygon()
    selection_type: str = ''
    selection: dict = field(default_factory=dict)
    preview: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    parameters: PathPlannerCfg = field(default_factory = lambda: pathplannercfg)
    subtasks: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    subtasks_parameters: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    tasks_order: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    tasks_order_parameters: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())

    def calc_route_preview(self, route: list) -> None:
        self.preview = pd.DataFrame(route)
        self.preview.columns = ['X', 'Y']
        self.preview['type'] = 'preview route'

    def create_subtask(self) -> None:
        if not self.subtasks.empty:
            task_nr = len(self.subtasks['task nr'].unique())
            filtered_df = self.subtasks[(self.subtasks['type'] == 'preview route') & (self.subtasks['task nr'] == task_nr-1)]
            start_position = {'X': [filtered_df.iloc[-1]['X']], 'Y': [filtered_df.iloc[-1]['Y']], 'type': ['start position']}
            position_df = pd.DataFrame(start_position)
        else:
            task_nr = 0
            start_position = {'X': [robot.position_x], 'Y': [robot.position_y], 'type': ['start position']}
            position_df = pd.DataFrame(start_position)
        subtask = self.preview
        selection = pd.DataFrame(self.selection)
        selection.columns = ['X', 'Y']
        selection['type'] = self.selection_type
        subtask = pd.concat([subtask, selection], ignore_index=True)
        subtask = pd.concat([subtask, position_df], ignore_index=True)
        subtask['map name'] = self.map_name
        subtask['task nr'] = task_nr
        self.subtasks = pd.concat([self.subtasks, subtask], ignore_index=True) 
        parameters = self.pathplanenrcfg_to_dict(task_nr)
        self.subtasks_parameters = pd.concat([self.subtasks_parameters, pd.DataFrame(parameters)], ignore_index= True)
        self.preview = pd.DataFrame()
    
    def pathplanenrcfg_to_dict(self, task_nr: int) -> dict:
        parameters = {'map name': self.map_name, 'task nr': task_nr, 'pattern': [self.parameters.pattern], 'width': [self.parameters.width], 'angle': [self.parameters.angle], 
                      'distancetoborder': [self.parameters.distancetoborder], 'mowarea': [self.parameters.mowarea], 'mowborder': [self.parameters.mowborder], 
                      'mowexclusion': [self.parameters.mowexclusion], 'mowborderccw': [self.parameters.mowborderccw]}
        return parameters
    
    def load_task_order(self, tasks_order: list) -> None:
        if tasks_order is not None and tasks_order != []:
            logger.debug(f'Load tasks: {tasks_order}')
            tasks_to_be_done = 0
            self.subtasks = pd.DataFrame()
            self.subtasks_parameters = pd.DataFrame()
            for task in tasks_order:
                subtasks = tasks.saved[(tasks.saved['name'] == task)&(tasks.saved['map name'] == current_map.name)]
                subtasks_parameters = tasks.saved_parameters[(tasks.saved_parameters['name'] == task)&(tasks.saved_parameters['map name'] == current_map.name)]
                for subtask_nr in subtasks['task nr'].unique():
                    subtask = subtasks[subtasks['task nr'] == subtask_nr]
                    subtask_parameters = subtasks_parameters[subtasks_parameters['task nr'] == subtask_nr]
                    subtask.loc[:, 'task nr'] = tasks_to_be_done
                    subtask_parameters.loc[:, 'task nr'] = tasks_to_be_done
                    self.subtasks = pd.concat([self.subtasks, subtask], ignore_index=True)
                    self.subtasks_parameters = pd.concat([self.subtasks_parameters, subtask_parameters], ignore_index=True)
                    tasks_to_be_done += 1
        else:
            logger.debug('No tasks to load')
            self.subtasks = pd.DataFrame()
            self.subtasks_parameters = pd.DataFrame()
    
    def create(self) -> None:
        self.name = ''
        self.map_name = current_map.name
        self.selected_perimeter = Polygon()
        self.selection_type = ''
        self.selection = dict()
        self.preview = pd.DataFrame()
        self.parameters = dict() 
        self.subtasks = pd.DataFrame()
        self.subtasks_parameters = pd.DataFrame()
        self.tasks_order = pd.DataFrame()
        self.tasks_order_parameters = pd.DataFrame()

@dataclass
class Tasks:
    selected: str = ''
    saved: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    saved_parameters: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())

current_map = Perimeter()
mapping_maps = Perimeters()
current_task = Task()
tasks = Tasks()

perimeter_mapping = pd.DataFrame()
perimeter_selected = pd.DataFrame()
perimeter_saved = pd.DataFrame()
perimeter = pd.DataFrame()
preview = pd.DataFrame()
imported = pd.DataFrame()

progress_color_palette = [
    "#78c2ad",
    "#78c2ad",
    "#78c2ad",
    "#78c2ad",
    "#78c2ad",
    "#78c2ad",
    #"goldenrod",
    #"blueviolet",
    #"cornflowerblue",
    #"lightcoral",
    #"lightslategrey",
]

tasks_color_palette = [
    "#78c2ad",
    "goldenrod",
    "blueviolet",
    "cornflowerblue",
    "lightcoral",
    "lightslategrey",
]
