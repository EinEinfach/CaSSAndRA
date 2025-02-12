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
    tasks_order = list(substasks['name'].unique())
    logger.info(f'Create route from task. Tasks order: {tasks_order}')
    route = []
    start_pos = calc_start_pos()
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
        if subtask_nr == 0:
            route = calc_simple(selected_perimeter, pathplannercfgtasktmp)
        else:
            route_tmp = calc(selected_perimeter, pathplannercfgtasktmp, route[-1])
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
    logger.info('Route calculation from task done')
    current_map.calc_route_preview(route)

def calc_simple(selected_perimeter: Polygon, parameters: PathPlannerCfg) -> list:
    route = []
    use_cassandra_pathfinder = False
    start_pos = calc_start_pos()
    route_tmp = calc(selected_perimeter, parameters, start_pos)
    if route_tmp == []:
        return []
    if use_cassandra_pathfinder:
        direct_way = current_map.check_direct_way(start_pos, route_tmp[0])
        if direct_way:
            route.append(start_pos)
            route.extend(route_tmp)
        else: 
            logger.info('Use cassandra pathfinder to connect start position to first point')  
            pathfinder.create()
            pathfinder.angle = 0
            route_astar = pathfinder.find_way(start_pos, route_tmp[0])  
            route_tmp.pop(0)
            route.extend(route_astar)
            route.extend(route_tmp)
    else:
        route = route_tmp
    return route 

def calc_start_pos() -> list:
    logger.info('Calc start position')
    start_pos = []
    current_pos = [robot.position_x, robot.position_y]

    #check if rover is docked
    if robot.job == 2 and not current_map.perimeter[current_map.perimeter['type'] == 'dockpoints'].empty:
        current_pos = current_map.perimeter[current_map.perimeter['type'] == 'dockpoints'].iloc[0][['X', 'Y']].tolist()

    #is rover within perimeter
    if Point(current_pos).within(current_map.perimeter_polygon) or Point(current_pos).touches(current_map.perimeter_polygon):
        logger.info(f'Start poisition is within perimeter')
        start_pos = current_pos
    #interpolate to nearest point
    else:
        border_points = current_map.perimeter_polygon.exterior.coords
        start_pos = [min(border_points, key=lambda coord: (coord[0]-current_pos[0])**2 + (coord[1]-current_pos[1])**2)]
    return start_pos
    

def calc(selected_perimeter: Polygon, parameters: PathPlannerCfg, start_pos: list = None) -> list:
    if start_pos == None:
        start_pos = calc_start_pos()
    if selected_perimeter.is_empty or (not parameters.mowarea and parameters.mowborder==0 and not parameters.mowexclusion):
        logger.info('Coverage path planner parameters are not valid. Calculation aborted.')
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
        if line_mask.is_empty and edge_polygons == [] and len(route) == 1:
            logger.info('No ways to calculate')
            return []
        route = lines.calcroute(border, line_mask, edge_polygons, route, parameters, angle)
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
        route2 = lines.calcroute(border, line_mask, [], list(last_coord.coords), parameters, angle+90)
        route2 = map.turn(route2, -angle-90)
        route.extend(list(route2.coords))
        # Clear progress bar
        current_map.total_progress = current_map.calculated_progress = 0
    
    if parameters.pattern == 'rings':
        border = current_map.perimeter_polygon
        area_to_mow = map.areatomow(selected_perimeter, parameters.distancetoborder, parameters.width)
        route, edge_polygons = cutedge.calcroute(selected_perimeter, parameters, list(start_pos.coords))
        if not parameters.mowarea:
            area_to_mow = Polygon()
        if area_to_mow.is_empty and edge_polygons == [] and len(route) == 1:
            logger.info('No ways to calculate')
            return []
        route = rings.calcroute(area_to_mow, border, edge_polygons, route, parameters)
        # Clear progress bar
        current_map.total_progress = current_map.calculated_progress = 0

    return route
