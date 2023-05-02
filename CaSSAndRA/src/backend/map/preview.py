import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *

from src.backend.data import mapdata
from . import map

def gotopoints(points: MultiPoint):
    preview_goto_points = pd.DataFrame(columns=['X', 'Y', 'type'])
    logger.info('Backend: Calc goto points preview')
    for point in points.geoms:
        coords_df = pd.DataFrame(point.coords)
        coords_df.columns = ['X','Y']
        coords_df['type'] = 'possible gotos'
        preview_goto_points = pd.concat([preview_goto_points, coords_df], ignore_index=True)
    
    mapdata.gotopoints = preview_goto_points

def gotopoint(clickdata: dict):
    logger.info('Backend: Writing data to mapdata.gotopoint')
    goto = {'X':[clickdata['points'][0]['x']], 'Y':[clickdata['points'][0]['y']], 'type': ['way']}
    mapdata.gotopoint = pd.DataFrame(goto)
    