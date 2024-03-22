import logging
logger = logging.getLogger(__name__)

from shapely.geometry import *

def check_direct_way(border: Polygon, start: list, end: list) -> bool:
    way = LineString([start, end])
    direct_way_possible = way.within(border)
    return direct_way_possible

def create_route(perimeter: Polygon, mowborder: str, mowexclusion: bool, 
                 mowborderccw: bool, last_coord: list, border: Polygon,
                 figure: str) -> list:
    route_tmp = []
    edges_pol = []
    if mowborder == 'yes':
        route_tmp = list(perimeter.exterior.coords)
        ###Remove double values###
        route_tmp = list(dict.fromkeys(route_tmp))
        ring = LinearRing(route_tmp)
        ###Check is counter clock wise###
        if not ring.is_ccw and mowborderccw == True:
            route_tmp.reverse()
        ###Look for shortest way from start point###
        first_coords = [min(route_tmp, key=lambda coord: (coord[0]-last_coord[0])**2 + (coord[1]-last_coord[1])**2)]
        first_coords_nr = route_tmp.index(first_coords[0])
        route_tmp = route_tmp[first_coords_nr:]+route_tmp[:first_coords_nr]
        route_tmp.append(route_tmp[0])
        if figure == 'MultiPolygon':
            direct_way_possible = check_direct_way(border, last_coord, route_tmp[0])
            if not direct_way_possible:
                logger.debug('Coverage path planner (planing route for cut to edge): No direct way for cut to edge possible, figure saved as to do for path planner')
                edges_pol.append(Polygon(perimeter.exterior.coords))
                route_tmp = []
    if mowexclusion == True:
        for i in range(len(perimeter.interiors)):
            edges_pol.append(Polygon(perimeter.interiors[i].coords))
    return route_tmp, edges_pol

def calcroute(area_to_mow, parameters, start):
    logger.info('Backend: Calc route for cutedge')
    mowoffs = -parameters.width
    if parameters.mowborder != 0:
        mowborder = 'yes'
    else:
        mowborder = 'no'
    mowexclusion = parameters.mowexclusion
    mowborderccw = parameters.mowborderccw
    rounds = parameters.mowborder
    num_edge_per = min(parameters.distancetoborder, 2)
    start_coords = start
    route = []
    route_tmp = []
    edges_pol = []

    area_to_mow_tmp = area_to_mow
    last_coord = start[0]
    for i in range(rounds):
        if area_to_mow_tmp.is_empty:
            logger.info('Coverage path planner (planing route for cut to edge): Could not finished distancetoborderloop, please check your settings. Max value: '+str(i))
            break
        elif area_to_mow_tmp.geom_type == 'MultiPolygon':
            logger.debug('Coverage path planner (planing route for cut to edge): MultiPolygon detected, creating loop')
            for single_polygon in area_to_mow_tmp.geoms:
                route_tmp, edges_pol_tmp = create_route(single_polygon, mowborder, mowexclusion, mowborderccw, last_coord, area_to_mow, 'MultiPolygon')
                logger.debug('Coverage path planner (planing route for cut to edge): Loop call delivered route: '+str(route_tmp))
                logger.debug('Coverage path planner (planing route for cut to edge): Loop call delivered figures to mow: '+str(len(edges_pol_tmp)))
                if route_tmp != []:
                    route.extend(route_tmp)
                    last_coord = route[-1]
                edges_pol.extend(edges_pol_tmp)
        elif area_to_mow_tmp.geom_type == 'Polygon':
            logger.debug('Coverage path planner (planing route for cut to edge): Polygon detected')
            route_tmp, edges_pol_tmp = create_route(area_to_mow_tmp, mowborder, mowexclusion, mowborderccw, last_coord, area_to_mow, 'Polygon')
            logger.debug('Coverage path planner (planing route for cut to edge): Call delivered route: '+str(route_tmp))
            logger.debug('Coverage path planner (planing route for cut to edge): Call delivered figures to mow: '+str(len(edges_pol_tmp)))
            if route_tmp != []:
                route.extend(route_tmp)
                last_coord = route[-1]
            edges_pol.extend(edges_pol_tmp)
        else:
            logger.error('Coverage path planner (planing route for cut to edge): Unknown figure, calculation incomplete. Shapely: '+area_to_mow_tmp.geom_type)
            break
    
        area_to_mow_tmp = area_to_mow_tmp.buffer(mowoffs, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
        area_to_mow_tmp = area_to_mow_tmp.simplify(0.05, preserve_topology=False)

    if route == []:
        route.extend(start)
    
    logger.info('Coverage path planner (planing route for cut to edge): Calculation finished')
    logger.debug('Coverage path planner (planing route for cut to edge): Route '+str(len(route))+' points; Exclusions to calculate: '+str(len(edges_pol)))
    return route, edges_pol