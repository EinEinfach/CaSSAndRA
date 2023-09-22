import logging
logger = logging.getLogger(__name__)

from shapely.geometry import *
from shapely.ops import *
from shapely import affinity
import pandas as pd
import networkx as nx

from ..data.mapdata import current_map

def turn_coords(coords: list, angle: int) -> list:
    if len(coords) < 2:
        figure = Point((coords))
    else:
        figure = LineString((coords))
    turned_figure = affinity.rotate(figure, angle, origin=(0, 0))
    turned_coords = list(turned_figure.coords)
    return turned_coords

def check_astar_distance(border: Polygon, possible_start: list, angle: int, route: list, perimeter_points) -> list:
    route_tmp = []
    reverse_line = None
    #Create start point  
    astar_start_tmp = Point((route[-1]))
    astar_start_tmp = affinity.rotate(astar_start_tmp, angle, origin=(0, 0))
    astar_start_tmp = nearest_points(astar_start_tmp, perimeter_points)
    astar_start = list(astar_start_tmp[1].coords)
    #Create end points
    #Create first end point
    coords_tmp1 = possible_start[0]
    coords_tmp1 = Point((coords_tmp1))
    coords_tmp1 = affinity.rotate(coords_tmp1, angle, origin=(0, 0))
    astar_end_tmp1 = nearest_points(perimeter_points, coords_tmp1)
    astar_end1 = list(astar_end_tmp1[0].coords)
    #Create second end point
    coords_tmp2 = possible_start[1]
    coords_tmp2 = Point((coords_tmp2))
    coords_tmp2 = affinity.rotate(coords_tmp2, angle, origin=(0, 0))
    astar_end_tmp2 = nearest_points(perimeter_points, coords_tmp2)
    astar_end2 = list(astar_end_tmp2[0].coords)
    try:
        astar_path1 = nx.astar_path(current_map.astar_graph, astar_start[0], astar_end1[0], heuristic=None, weight='weight')
        astar_path1 = turn_coords(astar_path1, -angle)
        way1 = [route[-1]]
        way1.extend(astar_path1)
        way1.extend([possible_start[0]])
        way1 = LineString((way1))
        way1_length = way1.length
        if not way1.within(border):
            way1 = None

        astar_path2 = nx.astar_path(current_map.astar_graph, astar_start[0], astar_end2[0], heuristic=None, weight='weight')
        astar_path2 = turn_coords(astar_path2, -angle)
        way2 = [route[-1]]
        way2.extend(astar_path2)
        way2.extend([possible_start[1]])
        way2 = LineString((way2))
        way2_length = way2.length
        if not way2.within(border):
            way2 = None
    except Exception as e:
        logger.warning('A* pathfinder delivered unexpexted result')
        logger.debug(str(e))
        return None, None, None
    if (way1 != None and way2 != None and way1_length <= way2_length) or (way1 != None and way2 == None):
        current_shortest_way_length = way1_length
        route_tmp = astar_path1
        reverse_line = False
    elif (way1 != None and way2 != None and way1_length > way2_length) or (way2 != None and way1 == None):
        current_shortest_way_length = way2_length
        route_tmp = astar_path2
        reverse_line = True
    else:
        return None, None, None
    return route_tmp, current_shortest_way_length, reverse_line

def check_prio_lines(ways_to_go: pd.DataFrame, border: Polygon, current_level: int, route: list, angle: int) -> list:
    possible_start = []
    gone_way = None
    #Standard call, look for lines: same level, level under, level over
    if current_level != None:
        #Check for prio lines 
        ways_area = ways_to_go[(ways_to_go['type'] == 'area') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True) & (ways_to_go['level_min'] <= current_level+1) & (ways_to_go['level_min']>=current_level-1)]
        if not ways_area.empty:
            #possible_start = list(ways_area['coords'])
            possible_start1 = min(ways_area['coords'], key=lambda coord: (coord[0][0]-route[-1][0])**2 + (coord[0][1]-route[-1][1])**2)
            possible_start2 = min(ways_area['coords'], key=lambda coord: (coord[1][0]-route[-1][0])**2 + (coord[1][1]-route[-1][1])**2)
            possible_start = [possible_start1, possible_start2]
            route_line_way, gone_way, length_to_line = shortest_path(border, possible_start, route, angle)
            return route_line_way, gone_way, length_to_line, possible_start
        else:
            #Check for all lines and pick the nearest two 
            ways_area = ways_to_go[(ways_to_go['type'] == 'area') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True)]
            if not ways_area.empty:
                possible_start1 = min(ways_area['coords'], key=lambda coord: (coord[0][0]-route[-1][0])**2 + (coord[0][1]-route[-1][1])**2)
                possible_start2 = min(ways_area['coords'], key=lambda coord: (coord[1][0]-route[-1][0])**2 + (coord[1][1]-route[-1][1])**2)
                possible_start = [possible_start1, possible_start2]
                route_line_way, gone_way, length_to_line = shortest_path(border, possible_start, route, angle)
                return route_line_way, gone_way, length_to_line, possible_start
            else:
                return None, None, None, None
    #If curren_level == None, then it is first call or no prio lines accessable
    if current_level == None or gone_way == None:
        ways_area = ways_to_go[(ways_to_go['type'] == 'area') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True)]
        if not ways_area.empty:
            possible_start1 = min(ways_area['coords'], key=lambda coord: (coord[0][0]-route[-1][0])**2 + (coord[0][1]-route[-1][1])**2)
            possible_start2 = min(ways_area['coords'], key=lambda coord: (coord[1][0]-route[-1][0])**2 + (coord[1][1]-route[-1][1])**2)
            possible_start = [possible_start1, possible_start2]
            route_line_way, gone_way, length_to_line = shortest_path(border, possible_start, route, angle)
            return route_line_way, gone_way, length_to_line, possible_start
        else:
            return None, None, None, None
    

def shortest_path_to_exclusion(border: Polygon, edges_to_check: list, route: list) -> list:
    end_of_route = route[-1]
    way_nr = None
    route_tmp = None
    current_shortest_way_coord = nearest_points(Point((end_of_route)), MultiPoint(edges_to_check[0].exterior.coords))
    current_shortest_way = LineString((current_shortest_way_coord))
    current_shortest_way_length = current_shortest_way.length
    #Handle shapely problem in case if linestring has length. Within perimeter delivers False
    if current_shortest_way_length == 0:
            current_shortest_way = Point((current_shortest_way_coord[0]))
    for i, edge in enumerate(edges_to_check):
        shortest_way_coord = nearest_points(Point((end_of_route)), MultiPoint(edge.exterior.coords))
        shortest_way = LineString((shortest_way_coord))
        shortest_way_length = shortest_way.length
        #Handle shapely problem in case if linestring has length. Within perimeter delivers False
        if shortest_way_length == 0:
            shortest_way = Point((shortest_way_coord[0]))
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

def shortest_path(border: Polygon, ways_to_check: list, route: list, angle: int) -> list:
    possible_line = ways_to_check[0]
    end_of_route = route[-1]
    current_shortest_way = LineString((end_of_route, possible_line[0])).length
    way_nr = None
    route_tmp = None
    for i, way in enumerate(ways_to_check):
        if way_nr != None and current_shortest_way < 2*0.18:
            break
        line_coord = way
        way_rev = way.copy()
        way_rev.reverse()
        line_coord_rev = way_rev
        way_to_line = LineString((end_of_route, line_coord[0]))
        length_of_way = way_to_line.length
        #Handle shapely problem in case if linestring has length. Within perimeter delivers False
        if length_of_way == 0:
            way_to_line = Point((end_of_route))
            length_of_way = 0
        way_to_line_rev = LineString((end_of_route, line_coord_rev[0]))
        length_of_rev_way = way_to_line_rev.length
        if length_of_rev_way == 0:
            way_to_line_rev = Point((end_of_route))
            length_of_rev_way = 0
        #Now check the shortest path, direct or reverse line
        if (length_of_way <= current_shortest_way and way_to_line.within(border)) or (length_of_way == 0 and way_to_line.touches(border)):
            current_shortest_way = length_of_way
            possible_line = line_coord
            way_nr = i
        if (length_of_rev_way < current_shortest_way and way_to_line_rev.within(border)) or (length_of_rev_way == 0 and way_to_line_rev.touches(border)):
            current_shortest_way = length_of_rev_way
            possible_line = line_coord_rev
            way_nr = i
        #No direct way for standar or reverse line, check A* distance
        if (not way_to_line.within(border) or not way_to_line_rev.within(border)):
            way_coord, length_of_astar_way, reverse_line = check_astar_distance(border, way, angle, route, current_map.perimeter_points)
            if (length_of_astar_way != None and length_of_astar_way < current_shortest_way) or (length_of_astar_way != None and way_nr == None):
                current_shortest_way = length_of_astar_way
                if reverse_line:
                    way_coord.extend(line_coord_rev)
                    possible_line = way_coord
                else:
                    way_coord.extend(line_coord)
                    possible_line = way_coord
                way_nr = i
    if way_nr != None:
        route_tmp = possible_line
    return route_tmp, way_nr, current_shortest_way


def calcroute(areatomow, border, line_mask, edges_pol, route, parameters, angle):
    logger.info('Coverage path planner (lines): Start coverage path planner')
    logger.debug(parameters)
    if len(route) == 1:
        logger.info('Coverage path planner (lines): Route is just start point, check if the point within perimeter')
        if not Point((route[-1])).within(border) or not Point((route[-1])).touches(border):
            logger.debug('Coverage path planner (lines): Rover is outside perimeter, interpolate to the border')
            route_tmp = border.exterior.coords
            route = [min(route_tmp, key=lambda coord: (coord[0]-route[-1][0])**2 + (coord[1]-route[-1][1])**2)]
            logger.info('Coverage path planner (lines): New start point: '+str(route))

    ways_to_go = pd.DataFrame()
    perimeter_points = current_map.perimeter_points

    tosimplify = False
    if parameters.distancetoborder == 0:
        logger.debug('Distance to border selected to 0, increase boundary')
        border = border.buffer(0.01, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
    else:
        logger.debug('Distance to border is not equal to 0, use original boundary')
    #Extract y-coordinate and sort data
    line_mask_coords = []
    #Check for data type MultiLineString or GeometryCollection as expected?
    logger.debug('Extract lines coordinates and sort data')
    try: 
        for line in line_mask.geoms:
            #Check if line is a point and create a virtual line
            if len(list(line.coords)) == 1:
                logger.debug('At least one line is a point, create a virtual line, and set simplify flag')
                tosimplify = True
                coords = list(line.coords)
                coords.extend(coords)
                line_mask_coords.append(coords)
            #Check if line is a line (as expected)
            else:
                line_mask_coords.append(list(line.coords))
    #There is no MultiLineString and no GeometryCollection. Selection to small?
    except:
        logger.debug('Line mask is no MultiLineString. Selection to small?')
        if not line_mask.is_empty:
            line = line_mask
            #Check if line is a point and create a virtual line
            if len(list(line.coords)) == 1:
                logger.debug('At least one line is a point, create a virtual line, and set simplify flag')
                tosimplify = True
                coords = list(line.coords)
                coords.extend(coords)
                line_mask_coords.append(coords)
             #Check if line is a line (as expected)
            else:
                line_mask_coords.append(list(line.coords))
        #Exctraction not possible
        else:
            logger.debug('Extraction not possible. Line mask is empty')
            line_mask_coords = []
    #Sort coordinates and create new MultiLineString
    line_mask_coords.sort(key=lambda x: x[0][1])
    result_lines = MultiLineString(line_mask_coords)
    logger.debug('Lines to calculate: '+str(len(result_lines.geoms)))

    #Add additional informations to edges to cut about y-position on the map
    logger.debug('Sort border cuts and exclusion cuts')
    logger.debug('Figures to sort: '+str(len(edges_pol)))
    border_bounds = border.bounds
    logger.debug('Border bounds: '+str(border_bounds))
    for i, pol in enumerate(edges_pol):
        bounds = pol.bounds
        logger.debug('Excl/borger to cut bounds: '+str(bounds))
        level_min = round((bounds[1] - border_bounds[1])/parameters.width)
        level_max = round((bounds[3]-border_bounds[1])/parameters.width)
        logger.debug('Add levels to excl/border to cut. Min: '+str(level_min)+' Max: '+str(level_max))
        edge = pd.DataFrame({'name': 'edge'+str(i),'shapely': pol, 'level_min': level_min, 'level_max': level_max, 'coords': [list(pol.exterior.coords)], 'type': 'edge', 'gone': False, 'take into account': True})
        ways_to_go = pd.concat([ways_to_go, edge], ignore_index=True)
    
    #Add additionl informations to the lines about y-position on the map
    logger.debug('Sort lines to cut')
    lines_to_go = []
    line_level = 0
    current_level = None
    if not result_lines.is_empty:
        coord = list(result_lines.geoms[0].coords)
        coord_y_old = coord[0][1]
        for i in range(len(result_lines.geoms)):
            coord = list(result_lines.geoms[i].coords)
            if coord[0][1] > coord_y_old:
                line_level += 1
            line = pd.DataFrame({'name': 'area'+str(i),'shapely': result_lines.geoms[i], 'level_min': line_level, 'level_max': line_level, 'coords': [coord], 'type': 'area', 'gone': False, 'take into account': True})
            ways_to_go = pd.concat([ways_to_go, line], ignore_index=True)
            coord_y_old = coord[0][1]
    else:
        logger.debug('No lines to sort found')
        line = pd.DataFrame({'name': 'area1','shapely': LineString(), 'level_min': None, 'level_max': None, 'coords': [None], 'type': 'area', 'gone': True, 'take into account': True})
        ways_to_go = pd.concat([ways_to_go, line], ignore_index= True)

    #Starting coverage path planner
    logger.info('Coverage path planner (calc lines): Starting loop')
    astar_path = []
    astar_last_way = []
    while True:
        gone_way = None
        gone_way_edge = None
        ways_to_go_filtered = ways_to_go[ways_to_go['gone'] == False]
        if ways_to_go_filtered.empty:
            logger.info('Coverage path planner (calc lines): No more way to calculate, ending loop')
            break

        #Check for ways to lines
        logger.debug('Check for prio lines')
        route_line_way, gone_way, length_to_line, possible_start = check_prio_lines(ways_to_go, border, current_level, route, angle)
        if gone_way != None:
            logger.debug('Found way to line, distance: '+str(length_to_line))

        #Check for possible ways to edges
        logger.debug('Check for edges to cut in range')
        #First call, current_level = None
        if current_level == None:
            ways_edge = ways_to_go[(ways_to_go['type'] == 'edge') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True)]
        else:
            ways_edge = ways_to_go[(ways_to_go['type'] == 'edge') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True) & (ways_to_go['level_min'] <= current_level) & (ways_to_go['level_max'] >= current_level)]
        if not ways_edge.empty:
            possible_edges = ways_edge.reset_index(drop=True)
            route_edge_way, gone_way_edge, length_to_edge = shortest_path_to_exclusion(border, possible_edges['shapely'].to_list(), route)
            if gone_way_edge != None:
                logger.debug('Found edge(s) to cut in range, distance: '+str(length_to_edge))
            else:
                logger.debug('No direct way to a edge found')
        else:
            logger.debug('No edges in range found')
        
        #Decide for a shortest way
        if gone_way != None and gone_way_edge != None:
            if length_to_line < 0.5*length_to_edge:
                index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==possible_start[gone_way])].index.array[0]
                ways_to_go.at[index, 'gone'] = True
                current_level = ways_to_go.at[index, 'level_min']
                logger.debug('Take way to a line, current level: '+str(ways_to_go.at[index, 'level_min'])+' Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
                astar_last_way = []
                route.extend(route_line_way)   
            else:
                index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==list(possible_edges.loc[gone_way_edge, 'shapely'].exterior.coords))].index.array[0] 
                ways_to_go.at[index, 'gone'] = True
                logger.debug('Take way to a edge, current level: '+str(ways_to_go.at[index, 'level_min'])+' Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
                astar_last_way = []
                route.extend(route_edge_way)
        elif gone_way != None:
            index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==possible_start[gone_way])].index.array[0]
            ways_to_go.at[index, 'gone'] = True
            current_level = ways_to_go.at[index, 'level_min']
            logger.debug('Take way to a line, current level: '+str(ways_to_go.at[index, 'level_min'])+' Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
            astar_last_way = []
            route.extend(route_line_way) 
        elif gone_way_edge != None:
            index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==list(possible_edges.loc[gone_way_edge, 'shapely'].exterior.coords))].index.array[0] 
            ways_to_go.at[index, 'gone'] = True
            logger.debug('Take way to a edge, current level: '+str(ways_to_go.at[index, 'level_min'])+' Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
            astar_last_way = []
            route.extend(route_edge_way)
        else:
            logger.debug('No point for start over direct way found. Starting A* pathfinder')
            #Check for ways to the lines
            astar_path = []
            if current_level != None:
                logger.debug('Check for lines')
                ways_area = ways_to_go[(ways_to_go['type'] == 'area') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True)]
                possible_start = list(ways_area['coords']) 
                if ways_area.empty:
                    logger.debug('No more lines to go')
                else:
                    for possible_way in possible_start:
                        route_line_way, length_of_astar_way, reverse_line = check_astar_distance(border, possible_way, angle, route, perimeter_points)
                        if route_line_way != None:
                            index = ways_to_go[ways_to_go['coords'].apply(lambda x: x==possible_way)].index.array[0]
                            ways_to_go.at[index, 'gone'] = True
                            current_level = ways_to_go.at[index, 'level_min']
                            logger.debug('Take way to a line, current level: '+str(ways_to_go.at[index, 'level_min'])+' Finished: '+str(len(ways_to_go[ways_to_go['gone']==True]))+'/'+str(len(ways_to_go)))  
                            astar_last_way = route_line_way
                            route.extend(route_line_way)
                            if reverse_line:
                                possible_way.reverse()
                            route.extend(possible_way)
                            break
            #Check for ways to edges
            #Create start point  
            ways_edge = ways_to_go[(ways_to_go['type'] == 'edge') & (ways_to_go['gone'] == False) & (ways_to_go['take into account'] == True)] 
            if not ways_edge.empty and route_line_way == None:
                astar_start_tmp = Point((route[-1]))
                astar_start_tmp = affinity.rotate(astar_start_tmp, angle, origin=(0, 0))
                astar_start_tmp = nearest_points(astar_start_tmp, perimeter_points)
                astar_start = list(astar_start_tmp[1].coords)
                logger.debug('Go for edge')
                possible_edges = ways_edge
                possible_edges = possible_edges.reset_index(drop=True)
                for i in range(len(possible_edges)):
                    coords_tmp = MultiPoint((list(possible_edges.at[i, 'shapely'].exterior.coords)))
                    coords_tmp = affinity.rotate(coords_tmp, angle, origin=(0, 0))
                    astar_end_tmp = nearest_points(perimeter_points, coords_tmp)
                    astar_end = list(astar_end_tmp[0].coords)
                    #Start A* pathfinder for edge route
                    try:
                        astar_path = nx.astar_path(current_map.astar_graph, astar_start[0], astar_end[0], heuristic=None, weight='weight')
                        if len(astar_path) < 2:
                            astar_path = Point((astar_path))
                        else:
                            astar_path = LineString((astar_path))
                        astar_path = affinity.rotate(astar_path, -angle, origin=(0, 0))  
                        astar_path = list(astar_path.coords)
                        #Check is the astar path within perimeter
                        astar_tmp = [route[-1]]
                        astar_tmp.extend(astar_path)
                        astar_end = affinity.rotate(astar_end_tmp[1], -angle, origin=(0,0))
                        astar_tmp.extend(list(astar_end.coords))
                        if not LineString((astar_tmp)).within(border):
                            logger.debug('A* pathfinder delivered invalid route, try another one')
                        else:
                            current_level = None
                            astar_last_way = astar_path
                            route.extend(astar_path)
                            logger.debug('A* pathfinder delivered route: '+str(astar_path))
                            break
                    except Exception as e:
                        logger.error('Coverage path planner (calc lines): A* pathfinder could not find a way')
                        logger.debug(str(e))
                        break
                
                if not LineString((astar_tmp)).within(border):
                    logger.debug('A* pathfinder delivered invalid route, reduce perimeter_points')
                    old_points = [list(point.coords) for point in perimeter_points.geoms]
                    if astar_start_tmp[1].equals(astar_end_tmp[0]):
                        old_points.remove(list(astar_start_tmp[1].coords))
                        logger.debug('Removed points: '+str(list(astar_start_tmp[1].coords)))
                    else:
                        old_points.remove(list(astar_start_tmp[1].coords))
                        old_points.remove(list(astar_end_tmp[0].coords))
                        logger.debug('Removed points: '+str(list(astar_start_tmp[1].coords))+' '+str(list(astar_end_tmp[0].coords)))
                    perimeter_points = MultiPoint((old_points))

            if astar_path == astar_last_way:
                logger.error('Coverage path planner (calc lines): A* caused an infintiy loop, path planning aborted')
                break

            if ways_edge.empty and route_line_way == None:
                logger.error('Backend: Unespected call in loop for pathfinder')
                break   
        
    route_shapely = LineString(route)
    return route_shapely
  

   

