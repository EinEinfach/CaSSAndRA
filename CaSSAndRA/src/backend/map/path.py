import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *

from . import map, cutedge, lines, rings
from ..data import mapdata
from ..data.mapdata import current_map
from ..data.cfgdata import PathPlannerCfg, pathplannercfgtasktmp
from ..data.roverdata import robot

def calc_task(substasks: pd.DataFrame, parameters: pd.DataFrame) -> None:
    logger.info('Backend: Create route from task')
    route = []
    start_pos = [robot.position_x, robot.position_y]
    for subtask_nr in substasks['task nr'].unique():
        subtask_df = substasks[substasks['task nr'] == subtask_nr]
        subtask_df = subtask_df.reset_index(drop=True)
        parameters_df = parameters[parameters['task nr'] == subtask_nr]
        parameters_df = parameters_df.reset_index(drop=True)
        if 'lassoPoints' in subtask_df['type'].unique():
            logger.debug('Task'+str(subtask_nr)+' lasso selection detected')
            x = subtask_df[subtask_df['type'] == 'lassoPoints']['X'].values.tolist()
            y = subtask_df[subtask_df['type'] == 'lassoPoints']['Y'].values.tolist()
            selection = {'x': x, 'y': y}
            selection = {'lassoPoints': selection}
            selected_perimeter = map.selection(current_map.perimeter_polygon, selection)
            
        elif 'range' in subtask_df['type'].unique():
            logger.debug('Task'+str(subtask_nr)+' range selection detected')
            x = subtask_df[subtask_df['type'] == 'range']['X'].values.tolist()
            y = subtask_df[subtask_df['type'] == 'range']['Y'].values.tolist()
            selection = {'x': x, 'y': y}
            selection = {'range': selection}
            selected_perimeter = map.selection(current_map.perimeter_polygon, selection)
        else:
            logger.debug('Task'+str(subtask_nr)+' no selection detected (Calc way for whole map)')
            selected_perimeter = current_map.perimeter_polygon
        pathplannercfgtasktmp.df_to_obj(parameters_df)
        route_tmp = calc(selected_perimeter, pathplannercfgtasktmp, start_pos)
        if subtask_nr == 0:
            route.extend(route_tmp)
        else:
            direct_way = current_map.check_direct_way(route[-1], route_tmp[0])
            if direct_way:
                logger.debug('Direct way possible. Connect tasks')
                route.extend(route_tmp)
            else:
                logger.debug('Direct way not possible. Starting A* pathfinder to connect tasks')
                astar_path = map.astar_path(current_map.perimeter_polygon, current_map.perimeter_points, current_map.astar_graph, route[-1], route_tmp[0])
                if astar_path == []:
                    logger.error('Backend: Route calculation from task could not be finished')
                    return
                route.extend(astar_path)
                route.extend(route_tmp)
        start_pos = route[-1]
    logger.info('Backend: Route calculation from task done')
    current_map.calc_route_preview(route)

def calc(selected_perimeter: Polygon, parameters: PathPlannerCfg, start_pos: list()) -> list:
    if selected_perimeter.is_empty:
        return
    logger.info('Backend: Planning route:')
    logger.info(parameters)
    logger.info('Rover start position: '+str(start_pos))
    start_pos = Point(start_pos)
    if parameters.pattern == 'lines' or parameters.pattern == 'squares':
        start_pos = map.turn(start_pos, parameters.angle)
        selected_area_turned = map.turn(selected_perimeter, parameters.angle)
        area_to_mow, border = map.border(selected_area_turned, parameters.distancetoborder, parameters.width)
        route, edge_polygons = cutedge.calcroute(border, parameters, list(start_pos.coords))
        line_mask = map.linemask(area_to_mow, parameters.width)
        route = lines.calcroute(area_to_mow, border, line_mask, edge_polygons, route, parameters, parameters.angle)
        route = map.turn(route, -parameters.angle)
        route = list(route.coords)

    if parameters.pattern == 'squares':
        last_coord = route[-1]
        last_coord = Point(last_coord)
        last_coord = map.turn(last_coord, parameters.angle+90)
        selected_area_turned = map.turn(selected_perimeter, parameters.angle+90)
        area_to_mow, border = map.border(selected_area_turned, parameters.distancetoborder, parameters.width)
        line_mask = map.linemask(area_to_mow, parameters.width)
        route2 = lines.calcroute(area_to_mow, border, line_mask, [], list(last_coord.coords), parameters, parameters.angle+90)
        route2 = map.turn(route2, -parameters.angle-90)
        route.extend(list(route2.coords))
    
    if parameters.pattern == 'rings':
        area_to_mow, border = map.border(selected_perimeter, parameters.distancetoborder, parameters.width)
        route, edge_polygons = cutedge.calcroute(border, parameters, list(start_pos.coords))
        route = rings.calcroute(area_to_mow, border, route, parameters)

    return route