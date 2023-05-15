import logging
logger = logging.getLogger(__name__)

import base64
import io
import os
import json
import pandas as pd
from dataclasses import dataclass
from shapely.geometry import *

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
    import_status: int = -1   
    select_imported_status: int = -1  

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