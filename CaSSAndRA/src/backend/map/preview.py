import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *

from src.backend.data import mapdata
from . import map
#import map

def lines(perimeter: Polygon, selection: dict(), mowoffset: float, mowangle: int):
    logger.info('Backend: Calc lines pattern preview') 
    perimeter_turned = map.turn(perimeter, mowangle)
    lines = map.linemask(perimeter_turned, mowoffset)
    lines = map.turn(lines, -mowangle)
    if selection == None:
        logger.info('Backend: Calculation of lines pattern preview finished. Transfer to data frame')
        mapdata.selected_perimeter = perimeter
    elif 'range' in selection:
        logger.info('Backend: Selection box detected. Preview with selected area.') 
        selection = selection['range']
        selected_polygon = box(selection['x'][0], selection['y'][0],
                               selection['x'][1], selection['y'][1])
        lines = lines.intersection(selected_polygon)
        mapdata.selected_perimeter = perimeter.intersection(selected_polygon)
    elif 'lassoPoints' in selection:
        logger.info('Backend: Selection lasso detected. Preview with selected area.')
        logger.debug('Lasso points: '+str(selection))
        selection = selection['lassoPoints']
        selection_list = list(zip(selection['x'], selection['y']))
        selected_polygon = Polygon(selection_list)
        if not selected_polygon.is_valid:
            logger.warning('Backend: Selection not valid, calculation aborted')
            lines = MultiLineString()
        else:
            lines = lines.intersection(selected_polygon)
            mapdata.selected_perimeter = perimeter.intersection(selected_polygon)
    else:
        logger.warning('Backend: Selection dict() unknown value')

    preview_lines = pd.DataFrame(columns=['X', 'Y', 'type'])
    try: 
        for i, line in enumerate(lines.geoms):
            coords_df = pd.DataFrame(line.coords)
            coords_df.columns = ['X','Y']
            coords_df['type'] = 'line_'+str(i)
            preview_lines = pd.concat([preview_lines, coords_df], ignore_index=True)
    except:
        logger.warning('Backend: Creation of data frame not possible. Selection to small?')
    
    mapdata.preview = preview_lines

def squares(perimeter: Polygon, selection: dict(), mowoffset: float, mowangle: int):
    logger.info('Backend: Calc squares pattern preview')
    perimeter_turned = map.turn(perimeter, mowangle)
    lines1 = map.linemask(perimeter_turned, mowoffset)
    lines1 = map.turn(lines1, -mowangle)
    perimeter_turned = map.turn(perimeter_turned, 90)
    lines2 = map.linemask(perimeter_turned, mowoffset)
    lines2 = map.turn(lines2, -(mowangle+90))

    if selection == None:
        logger.info('Backend: Calculation of squares pattern preview finished. Transfer to data frame')
        mapdata.selected_perimeter = perimeter
    elif 'range' in selection:
        logger.info('Backend: Selection box detected. Preview with selected area.') 
        selection = selection['range']
        selected_polygon = box(selection['x'][0], selection['y'][0],
                               selection['x'][1], selection['y'][1])
        lines1 = lines1.intersection(selected_polygon)
        lines2 = lines2.intersection(selected_polygon)
        mapdata.selected_perimeter = perimeter.intersection(selected_polygon)
    elif 'lassoPoints' in selection:
        logger.info('Backend: Selection lasso detected. Preview with selected area.')
        selection = selection['lassoPoints']
        selection_list = list(zip(selection['x'], selection['y']))
        selected_polygon = Polygon(selection_list)
        if not selected_polygon.is_valid:
            logger.warning('Backend: Selection not valid, calculation aborted')
            lines1 = MultiLineString()
            lines2 = MultiLineString()
        else:
            lines1 = lines1.intersection(selected_polygon)
            lines2 = lines2.intersection(selected_polygon)
            mapdata.selected_perimeter = perimeter.intersection(selected_polygon)
    else:
        logger.warning('Backend: Selection dict() unknown value')
    
    preview_squares = pd.DataFrame(columns=['X', 'Y', 'type'])
    try: 
        for i, line in enumerate(lines1.geoms):
            coords_df = pd.DataFrame(line.coords)
            coords_df.columns = ['X','Y']
            coords_df['type'] = 'line_'+str(i)
            preview_squares = pd.concat([preview_squares, coords_df], ignore_index=True)
        for i, line in enumerate(lines2.geoms):
            coords_df = pd.DataFrame(line.coords)
            coords_df.columns = ['X','Y']
            coords_df['type'] = 'line_'+str(len(lines1.geoms)+i)
            preview_squares = pd.concat([preview_squares, coords_df], ignore_index=True)
    except:
        logger.warning('Backend: Creation of data frame not possible. Selection to small?')
    
    mapdata.preview = preview_squares

def calc(pattern: str(), perimeter: Polygon, selection: dict(), mowoffset: float, mowangle: int):
    if pattern == 'lines':
        lines(perimeter, selection, mowoffset, mowangle)
    elif pattern == 'squares':
        squares(perimeter, selection, mowoffset, mowangle)

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
    