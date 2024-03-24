import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *
import random, math

from . import map, cutedge, lines, rings
from . pathfinder import pathfinder
from ..data.mapdata import current_map
from ..data.cfgdata import PathPlannerCfg, pathplannercfgtasktmp
from ..data.roverdata import robot

def calc_task(substasks: pd.DataFrame, parameters: pd.DataFrame) -> None:
    logger.info('Backend: Create route from task')
    route = []
    start_pos = [robot.position_x, robot.position_y]
    areatomow = Polygon()

    current_map.total_tasks = substasks['task nr'].nunique()

    for subtask_nr in substasks['task nr'].unique():
        current_map.task_progress = subtask_nr
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
                logger.debug('Direct way not possible. Starting pathfinder to connect tasks')
                pathfinder.create()
                pathfinder.angle = 0
                route_astar = pathfinder.find_way(route[-1], route_tmp[0])
                if route_astar == []:
                    logger.error('Backend: Route calculation from task could not be finished')
                    return
                del route_astar[-1] #remove last point it is given by legacy route (second task start point)
                route.extend(route_astar)
                route.extend(route_tmp)
        start_pos = route[-1]
        #Extend areatomow value
        if areatomow == Polygon():
            areatomow = selected_perimeter
        else:
            areatomow = areatomow.union(selected_perimeter)
    current_map.areatomow = round(areatomow.area)
    logger.info('Backend: Route calculation from task done')
    current_map.calc_route_preview(route)

def calc(selected_perimeter: Polygon, parameters: PathPlannerCfg, start_pos: list) -> list:
    if selected_perimeter.is_empty or (not parameters.mowarea and parameters.mowborder==0 and not parameters.mowexclusion):
        logger.info(f"Coverage path planner parameters are not valid. Calculation aborted.")
        logger.debug(parameters)
        return []
    logger.info('Backend: Planning route:')
    logger.info(parameters)
    logger.info('Rover start position: '+str(start_pos))
    start_pos = Point(start_pos)
    #check if random angle
    if parameters.angle == None or math.isnan(float(parameters.angle)):
        angle = random.randrange(start=359) 
        logger.debug(f'Coverage path planner uses random angle: {angle}Deg')
    else:
        angle = parameters.angle

    if parameters.pattern == 'lines' or parameters.pattern == 'squares':
        start_pos = map.turn(start_pos, angle)
        selected_area_turned = map.turn(selected_perimeter, angle)
        border = map.turn(current_map.perimeter_polygon, angle)
        area_to_mow = map.areatomow(selected_area_turned, parameters.distancetoborder, parameters.width)
        route, edge_polygons = cutedge.calcroute(selected_area_turned, parameters, list(start_pos.coords))
        if parameters.mowarea:
            line_mask = map.linemask(area_to_mow, parameters.width)
        else:
            line_mask = MultiLineString()
        route = lines.calcroute(area_to_mow, border, line_mask, edge_polygons, route, parameters, angle)
        route = map.turn(route, -angle)
        route = list(route.coords)
        # Clear progress bar
        if parameters.pattern == 'lines' or (parameters.pattern == 'squares' and parameters.mowarea != True):
            current_map.total_progress = current_map.calculated_progress = 0

    if parameters.pattern == 'squares' and parameters.mowarea == True:
        last_coord = route[-1]
        last_coord = Point(last_coord)
        last_coord = map.turn(last_coord, angle+90)
        selected_area_turned = map.turn(selected_perimeter, angle+90)
        border = map.turn(current_map.perimeter_polygon, angle+90)
        area_to_mow = map.areatomow(selected_area_turned, parameters.distancetoborder, parameters.width)
        if parameters.mowarea:
            line_mask = map.linemask(area_to_mow, parameters.width)
        else:
            line_mask = MultiLineString()
        route2 = lines.calcroute(area_to_mow, border, line_mask, [], list(last_coord.coords), parameters, angle+90)
        route2 = map.turn(route2, -angle-90)
        route.extend(list(route2.coords))
        # Clear progress bar
        current_map.total_progress = current_map.calculated_progress = 0
    
    if parameters.pattern == 'rings':
        border = current_map.perimeter_polygon
        area_to_mow = map.areatomow(selected_perimeter, parameters.distancetoborder, parameters.width)
        route, edge_polygons = cutedge.calcroute(selected_perimeter, parameters, list(start_pos.coords))
        route = rings.calcroute(area_to_mow, border, route, parameters)
        # Clear progress bar
        current_map.total_progress = current_map.calculated_progress = 0

    return route
