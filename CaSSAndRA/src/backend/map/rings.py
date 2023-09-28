import logging
logger = logging.getLogger(__name__)

from shapely.geometry import *
from shapely.ops import *
import pandas as pd
import networkx as nx

from ..data.mapdata import current_map
from .pathfinder import pathfinder

def shortest_path_to_point(border: Polygon, points_to_check: list, route: list) -> list:
    end_of_route = route[-1]
    way_nr = None
    route_tmp = None
    current_shortest_way_coord = [end_of_route, list(points_to_check[0].coords)[0]]
    current_shortest_way = LineString(current_shortest_way_coord)
    current_shortest_way_length = current_shortest_way.length
    #Handle shapely problem in case if linestring has length. Within perimeter delivers False
    if current_shortest_way_length == 0:
        current_shortest_way = Point((current_shortest_way_coord[0]))
    for i, point in enumerate(points_to_check):
        shortest_way_coord = [end_of_route, list(point.coords)[0]]
        shortest_way = LineString((shortest_way_coord))
        shortest_way_length = shortest_way.length
        #Handle shapely problem in case if linestring has length. Within perimeter delivers False
        if shortest_way_length == 0:
            shortest_way = Point((shortest_way_coord[0]))
        if (shortest_way_length <= current_shortest_way_length and shortest_way.within(border)) or (shortest_way_length == 0 and shortest_way.touches(border)):
            current_shortest_way_length = shortest_way_length
            route_tmp = list(point.coords)
            way_nr = i
    return route_tmp, way_nr, current_shortest_way_length

def shortest_path_to_exclusion(border: Polygon, edges_to_check: list, route: list) -> list:
    end_of_route = route[-1]
    way_nr = None
    route_tmp = None
    current_shortest_way_coord = nearest_points(Point((end_of_route)), MultiPoint(edges_to_check[0].exterior.coords))
    current_shortest_way = LineString((current_shortest_way_coord))
    current_shortest_way_length = current_shortest_way.length
    #Handle shapely problem in case if linestring has length. Within perimeter delivers False
    if current_shortest_way_length <= 0.01:
        current_shortest_way_length = 0
        current_shortest_way = Point((current_shortest_way_coord[1]))
    for i, edge in enumerate(edges_to_check):
        shortest_way_coord = nearest_points(Point((end_of_route)), MultiPoint(edge.exterior.coords))
        shortest_way = LineString((shortest_way_coord))
        shortest_way_length = shortest_way.length
        #Handle shapely problem in case if linestring has length. Within perimeter delivers False
        if shortest_way_length <= 0.01:
            shortest_way_length = 0
            shortest_way = Point((shortest_way_coord[1]))
        if (shortest_way_length <= current_shortest_way_length and shortest_way.within(border)) or (shortest_way_length == 0 and shortest_way.touches(border)):
            current_shortest_way_length = shortest_way_length
            route_tmp = list(edge.exterior.coords)
            route_tmp.pop(-1)
            first_coords_nr = route_tmp.index(list(shortest_way_coord[-1].coords)[0])
            route_tmp = route_tmp[first_coords_nr:]+route_tmp[:first_coords_nr]
            route_tmp.append(route_tmp[0])
            #Check for cw or ccw, which way shorter
            route_1 = [route[-1]]
            route_1.extend(route_tmp)
            route_2 = [route[-1]]
            route_tmp.reverse()
            route_2.extend(route_tmp)
            route1_length = LineString((route_1)).length
            route2_length = LineString((route_2)).length
            if route1_length < route2_length:
                route_tmp.reverse()
            way_nr = i
    return route_tmp, way_nr, current_shortest_way_length

def split_multipolygons(current_polygons: MultiPolygon, width: float) -> list:
    polygons = []
    for polygon in current_polygons.geoms:
        polygons.extend(create_polygons(polygon, width))
    return polygons

def create_polygons(current_polygon: Polygon, width: float) -> list:
    polygons = []
    perimeter_coords = list(current_polygon.exterior.coords)
    polygons.append(Polygon((perimeter_coords)))
    #Check if perimeter is last polygon and add a centroid
    last_polygon = current_polygon.buffer(width, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
    last_polygon = last_polygon.simplify(0.02, preserve_topology=False)
    if last_polygon.is_empty:
        centroid = current_polygon.centroid
        polygons.append(centroid)
    for exclusion in current_polygon.interiors:
        exclusion_coords = exclusion.coords
        polygons.append(Polygon((exclusion_coords)))
    return polygons

def calcroute(areatomow, border, route, parameters):
    logger.info('Coverage path planner (rings): Start coverage path planner')
    mowccw = parameters.mowborderccw
    logger.debug(parameters)
    pathfinder.create()
    pathfinder.angle = 0
    if len(route) == 1:
        logger.info('Coverage path planner (rings): Route is just start point, check if the point within perimeter')
        if not Point((route[-1])).within(border) or not Point((route[-1])).touches(border):
            logger.debug('Coverage path planner (rings): Rover is outside perimeter, interpolate to the border')
            route_tmp = border.exterior.coords
            route = [min(route_tmp, key=lambda coord: (coord[0]-route[-1][0])**2 + (coord[1]-route[-1][1])**2)]
            logger.info('Coverage path planner (rings): New start point: '+str(route))
    
    logger.info('Coverage path planner (rings): Create polygons')
    areatomow_tmp = areatomow
    polygons = []
    while True:
        if areatomow_tmp.is_empty:
            logger.info('Coverage path planner (rings): Calculation done')
            break
        if areatomow_tmp.geom_type == 'Polygon':
            polygons.extend(create_polygons(areatomow_tmp, -parameters.width))
        elif areatomow_tmp.geom_type == 'MultiPolygon':
            polygons.extend(split_multipolygons(areatomow_tmp, -parameters.width))
        else:
            logger.warning('Unknown figure')
            break
        areatomow_tmp = areatomow_tmp.buffer(-parameters.width, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
        areatomow_tmp = areatomow_tmp.simplify(0.02, preserve_topology=False)
    logger.info('Coverage path planner (rings): Polygons created. Polygons to calculate: '+str(len(polygons)))

    logger.info('Coverage path planner (calc rings): Create ways')
    ways_to_go = pd.DataFrame()
    for i, polygon in enumerate(polygons):
        if polygon.geom_type == 'Polygon':
            pol_df = pd.DataFrame({'name': 'polygon'+str(i), 'shapely': polygon, 'coords': [list(polygon.exterior.coords)], 'type': 'polygon', 'gone': False, 'take into account': True})
        else:
            pol_df = pd.DataFrame({'name': 'polygon'+str(i), 'shapely': polygon, 'coords': [list(polygon.coords)], 'type': 'point', 'gone': False, 'take into account': True})
        ways_to_go = pd.concat([ways_to_go, pol_df], ignore_index=True)
    
    logger.info('Coverage path planner (calc rings): Starting loop')
    while True:
        gone_way_pol = None
        gone_way_pt = None
        ways = ways_to_go[ways_to_go['gone'] == False]
        if ways.empty:
            logger.info('Coverage path planner (calc rings): Calculation done')
            break
        ways_polygons = ways_to_go[(ways_to_go['type'] == 'polygon') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True)]
        ways_points = ways_to_go[(ways_to_go['type'] == 'point') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True)]
        logger.debug('Check for polygons to cut in range')
        if not ways_polygons.empty:
            possible_pol = ways_polygons
            possible_pol = possible_pol.reset_index(drop=True)
            route_pol_way, gone_way_pol, length_to_pol = shortest_path_to_exclusion(border, possible_pol['shapely'].to_list(), route)  
        else:
            logger.debug('No direct way to a polygon found')
        if not ways_points.empty:
            possible_pt = ways_points
            possible_pt = possible_pt.reset_index(drop=True)
            route_pt_way, gone_way_pt, length_to_pt = shortest_path_to_point(border, possible_pt['shapely'].to_list(), route)
        #Decide for a shortest way
        if gone_way_pol != None and gone_way_pt != None:
            if length_to_pol < length_to_pt:
                index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==list(possible_pol.loc[gone_way_pol, 'shapely'].exterior.coords))].index.array[0] 
                ways_to_go.at[index, 'gone'] = True
                logger.debug('Found way to a polygon: Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
                route.extend(route_pol_way)  
                # Progress-bar data
                current_map.total_progress = len(ways_to_go)
                current_map.calculated_progress = len(ways_to_go[ways_to_go['gone']==True])
            else:
                index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==list(possible_pt.loc[gone_way_pt, 'shapely'].coords))].index.array[0]
                ways_to_go.at[index, 'gone'] = True
                logger.debug('Found way to a point: Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
                route.extend(route_pt_way)
                # Progress-bar data
                current_map.total_progress = len(ways_to_go)
                current_map.calculated_progress = len(ways_to_go[ways_to_go['gone']==True])
        elif gone_way_pol != None:
            index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==list(possible_pol.loc[gone_way_pol, 'shapely'].exterior.coords))].index.array[0] 
            ways_to_go.at[index, 'gone'] = True
            logger.debug('Found way to a polygon: Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
            route.extend(route_pol_way)
            # Progress-bar data
            current_map.total_progress = len(ways_to_go)
            current_map.calculated_progress = len(ways_to_go[ways_to_go['gone']==True])
        elif gone_way_pt != None:
            index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==list(possible_pt.loc[gone_way_pt, 'shapely'].coords))].index.array[0]
            ways_to_go.at[index, 'gone'] = True
            logger.debug('Found way to a point: Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
            route.extend(route_pt_way)
            # Progress-bar data
            current_map.total_progress = len(ways_to_go)
            current_map.calculated_progress = len(ways_to_go[ways_to_go['gone']==True])
        else:
            logger.debug('No point for start over direct way found. Starting A* pathfinder') 
            possible_goals = ways_to_go[ways_to_go['gone'] == False]
            for i in range(len(possible_goals)):
                if not possible_goals.empty:
                    if possible_goals.iloc[i]['type'] == 'polygon':
                        goal = nearest_points(Point(route[-1]), MultiPoint((list(possible_goals.iloc[i]['shapely'].exterior.coords))))[1]
                    else:
                        goal = nearest_points(Point(route[-1]), Point((list(possible_goals.iloc[i]['shapely'].coords))))[1]
                    goal = list(goal.coords)
                route_astar = pathfinder.find_way(route[-1], goal)
                if route_astar != []:
                    index = possible_goals.index.values[0]
                    route.extend(route_astar)
                    break
            if route_astar == []:
                logger.warning('Coverage patha planner (rings): Could not finish calculation')
                break
           
    return route