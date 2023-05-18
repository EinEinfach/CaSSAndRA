import logging
logger = logging.getLogger(__name__)

import base64
import io
import os
import json
import pandas as pd
import math
from dataclasses import dataclass
from shapely.geometry import *

from .roverdata import robot
from .. map import map

@dataclass
class Perimeter:
    name: str() = ''
    perimeter: pd.DataFrame = pd.DataFrame()
    perimeter_polygon: Polygon = Polygon()
    perimeter_for_plot: pd.DataFrame = pd.DataFrame()
    gotopoints: pd.DataFrame = pd.DataFrame()
    gotopoint: pd.DataFrame = pd.DataFrame()
    mowpath: pd.DataFrame = pd.DataFrame()
    preview: pd.DataFrame = pd.DataFrame()
    areatomow: float() = 0
    distancetogo: float() = 0

    def set_gotopoint(self, clickdata: dict) -> None:
        goto = {'X':[clickdata['points'][0]['x']], 'Y':[clickdata['points'][0]['y']], 'type': ['way']}
        self.gotopoint = pd.DataFrame(goto)

    def create_perimeter_polygon(self) -> None:
        df = self.perimeter
        perimeter = df[df['type'] == 'perimeter']
        df = df[df['type'] != 'perimeter']
        df = df[df['type'] != 'way']
        df = df[df['type'] != 'dockpoints']
        perimeter_coords = perimeter[['X', 'Y']]
        #create perimeter
        perimeter = Polygon(perimeter_coords.values.tolist())
        #create exclusions
        for exclusion in pd.unique(df['type']):
            exclusions = df[df['type'] == exclusion]
            exclusion_coords = exclusions[['X', 'Y']]
            exclusions = Polygon(exclusion_coords.values.tolist())
            perimeter = perimeter.difference(exclusions)
        self.perimeter_polygon = perimeter
    
    def create_perimeter_for_plot(self) -> None:
        self.perimeter_for_plot = pd.DataFrame()
        perimeter = self.perimeter
        #Add first value to the end, if perimeter or exclusion
        types = perimeter['type'].unique()
        for type in types:
            if type != 'dockpoints':
                coords = perimeter[perimeter['type'] == type]
                first_value_cpy = coords.iloc[:1,:]
                coords = pd.concat([coords, first_value_cpy], ignore_index=True)
                self.perimeter_for_plot = pd.concat([self.perimeter_for_plot, coords], ignore_index=True)
            else:
                coords = perimeter[perimeter['type'] == type]
                self.perimeter_for_plot = pd.concat([self.perimeter_for_plot, coords], ignore_index=True)
    
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
    
    def create(self, name: str()) -> None:
        self.name = name
        self.preview = pd.DataFrame()
        self.mowpath = pd.DataFrame()
        self.create_perimeter_polygon()
        self.create_perimeter_for_plot()
        self.create_go_to_points()
        self.save_map_name()
    
    def calc_route_preview(self, route: list()) -> None:
        self.preview = pd.DataFrame(route)
        self.preview.columns = ['X', 'Y']
        self.preview['type'] = 'preview route'
    
    def read_map_name(self) -> str():
        absolute_path = os.path.dirname(__file__)
        try:
            with open(absolute_path.replace('/src/backend/data', '/src/data/map/tmp.json')) as f: 
                tmp_data = json.load(f)
                f.close()
                return tmp_data['PERIMETERNAME']
        except Exception as e:
            logger.error('Backend: Could not read data from file. Missing tmp.json')
            logger.debug(str(e))
            return ''
    
    def save_map_name(self) -> None:
        absolute_path = os.path.dirname(__file__)
        tmp_data = {'PERIMETERNAME': self.name}
        try:
            with open(absolute_path.replace('/src/backend/data', '/src/data/map/tmp.json'), 'w') as f:
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
        perimeter_polygon = Polygon()
        perimeter_for_plot = pd.DataFrame()
        gotopoints = pd.DataFrame()
        gotopoint = pd.DataFrame()
        mowpath = pd.DataFrame()
        preview = pd.DataFrame()
        areatomow = 0
        distancetogo = 0
        self.save_map_name()

@dataclass
class Perimeters:
    selected: str() = ''
    imported: pd.DataFrame = pd.DataFrame()
    selected_import: pd.DataFrame = pd.DataFrame()
    saved: pd.DataFrame = pd.DataFrame()
    selected_save: pd.DataFrame = pd.DataFrame()
    build: pd.DataFrame = pd.DataFrame()
    dockpoints: pd.DataFrame = pd.DataFrame()
    import_status: int = -1   
    select_imported_status: int = -1  

    def init(self) -> None:
        self.selected = ''
        self.selected_save = pd.DataFrame()
        self.build = pd.DataFrame()
        self.dockpoints = pd.DataFrame()

    def import_sunray(self, content: str()) -> None:
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
        
    def select_imported(self, nr: int()) -> None:
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
        self.selected_save = perimeter[['X', 'Y', 'type', 'name']]
        self.build = perimeter[['X', 'Y', 'type', 'name']]
        self.dockpoints = self.build[self.build['type'] == 'dockpoints']

    def add_point(self, create: str()) -> None:
        logger.debug('Mapping add point: '+str(robot.position_x)+' '+str(robot.position_y))
        #remove unfinished figure
        if create != 'figure' and not self.build.empty:
            logger.debug('Mapping remove unfinished figure')
            self.build = self.build[self.build['type'] != 'figure']
        #create point and add to data frame
        point = {'X': [robot.position_x], 'Y': [robot.position_y], 'type': [create]}
        df = pd.DataFrame(point)
        logger.debug('Mapping moved data to data frame: '+str(point))
        df.columns = ['X', 'Y', 'type']
        self.build = pd.concat([self.build, df], ignore_index=True)
        
    def remove_point(self, create: str()) -> None:
        logger.debug('Mapping removing last point')
        df = self.build[self.build['type'] == create]
        if not df.empty:
            self.build = self.build[:-1]
    
    def add_figure(self, selection: dict()) -> None:
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

    def figure_action(self, action: str()) -> None:
        logger.debug('Mapping finish figure as: '+action)
        df = self.build[self.build['type'] == 'figure']
        df['type'] = 'perimeter'
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
        else:
            new_perimeter = old_perimeter.difference(new_perimeter)
            if new_perimeter.geom_type != 'Polygon':
                logger.warning('Backend: Could not create new perimeter, new figure is: '+new_perimeter.geom_type)
                new_perimeter = old_perimeter
        logger.debug('Mapping new perimeter is empty: '+str(new_perimeter.is_empty))
        if new_perimeter.is_empty:
            logger.debug('Mapping ignore figure create empty data frame')
            self.build = pd.DataFrame()
        else:
            logger.debug('Mapping create a new data frame')
            dockpoints = self.build[self.build['type'] == 'dockpoints']
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

    def is_changed(self) -> bool:
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
    
    def check_dockpoints(self) -> None:
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
                    new_vector = [math.cos(last_vector_angle)*0.1, math.sin(last_vector_angle)*0.1]
                    new_last_coord = [last_coord[0]+new_vector[0], last_coord[1]+new_vector[1]]
                    self.build.iloc[-1, self.build.columns.get_loc('X')] = new_last_coord[0]
                    self.build.iloc[-1, self.build.columns.get_loc('Y')] = new_last_coord[1]
                    logger.debug('Mapping dockpoints are changed, the lastpoint is adjusted. Old values: '+str(last_coord)+' New values: '+str(new_last_coord))
        else:
            logger.debug('Mapping new map is an empty dataframe, dockpoints are not changed, adjustment not neccessary')
    


           



current_map = Perimeter()
mapping_maps = Perimeters()

perimeter_mapping = pd.DataFrame()
perimeter_selected = pd.DataFrame()
perimeter_saved = pd.DataFrame()
perimeter = pd.DataFrame()
preview = pd.DataFrame()
imported = pd.DataFrame()


#areatomow = float()
#distancetogo = float()
#perimeter_for_plot contains the same data as perimeter and aditionaly the first coordiante for perimeter and every exclusion for creating a closed polygon in plot
#perimeter_for_plot = pd.DataFrame()

#map interaction data
selected_zone = pd.DataFrame()
zone = pd.DataFrame()

#mow settings from mapcfg.json
mowoffset = float()
mowangle = int()
mowedge = bool()
distancetoborder = int()
pattern = str()

#positionmode from mapcfg.json
positionmode = str()
lon = float()
lat = float()

#mow settings from state page
mowoffsetstatepage = float()
mowanglestatepage = int()
mowedgestatepage = bool()
distancetoborderstatepage = int()
patternstatepage = str()

#temp mapdata
selected_perimeter = Polygon()