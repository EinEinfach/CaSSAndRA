import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *
from shapely import affinity
from shapely.ops import *
import networkx as nx

def selection(perimeter: Polygon, selection: dict) -> Polygon:
    try: 
        logger.info('Check for selection and create a new perimter if there')
        logger.debug('perimeter coords: '+str(perimeter.exterior.coords)+' selection: '+str(selection))

        if selection == None:
            logger.info('No selection detected, go further with whole perimeter')
            return perimeter
        
        elif 'range' in selection:
            logger.info('Selection box detected. Create an new perimeter with box select.') 
            selection = selection['range']
            selected_polygon = box(selection['x'][0], selection['y'][0],
                                selection['x'][1], selection['y'][1])
            new_perimeter = perimeter.intersection(selected_polygon)
            return new_perimeter
        
        elif 'lassoPoints' in selection:
            logger.info('Selection lasso detected. Create a new perimeter with lasso select.')
            logger.debug('Lasso points: '+str(selection))
            selection = selection['lassoPoints']
            selection_list = list(zip(selection['x'], selection['y']))
            selected_polygon = Polygon(selection_list)
            if not selected_polygon.is_valid:
                logger.warning('Selection not valid, take convex hull')
                selected_polygon = selected_polygon.convex_hull
            new_perimeter = perimeter.intersection(selected_polygon)
            return new_perimeter
        
        elif 'api' in selection:
            logger.info('Selection via api. Create new perimeter with api select.')
            logger.debug(f'API points: {selection}')
            selection = selection['api']
            selection_list = list(zip(selection['x'], selection['y']))
            selected_polygon = Polygon(selection_list)
            if not selected_polygon.is_valid:
                logger.warning('Selection not valid, calculation aborted')
                return Polygon()
            else:
                new_perimeter = perimeter.intersection(selected_polygon)
                return new_perimeter

        else:
            logger.warning('Backend: Map selection failed. Selection dict() is an unknown value')
            return Polygon()
    except Exception as e:
        logger.warning('Backend: Map selection failed')
        logger.debug(str(e))

def create(map: pd.DataFrame) -> Polygon:
    logger.info('Backend: Create a shapely figure from data frame')
    perimeter = map[map['type'] == 'perimeter']
    map = map[map['type'] != 'perimeter']
    map = map[map['type'] != 'way']
    map = map[map['type'] != 'dockpoints']
    map = map[map['type'] != 'search wire']
    perimeter_coords = perimeter[['X', 'Y']]
    #create perimeter
    perimeter = Polygon(perimeter_coords.values.tolist())
    #create exclusions
    for exclusion in pd.unique(map['type']):
        exclusions = map[map['type'] == exclusion]
        exclusion_coords = exclusions[['X', 'Y']]
        exclusions = Polygon(exclusion_coords.values.tolist())
        perimeter = perimeter.difference(exclusions)
    return perimeter

def turn(figure: Polygon, mowangle: int) -> Polygon:
    try: 
        logger.info('Backend: Turning shapely figure: '+figure.geom_type+' Angle: {}'.format(-mowangle))
        logger.debug(str(figure))
        figure_rotated = affinity.rotate(figure, -mowangle, origin=(0, 0))
        return figure_rotated
    except Exception as e:
        logger.warning('Backend: Shapely figure turning failed')
        logger.debug(str(e))
        if figure.geom_type == 'Polygon': #Fix failure where some users have problem with polygon turning (no closed ring)
            logger.debug("Failed figure is polygon. Trying to turn perimeter coordinates")
            perimeter_points = MultiPoint(list(figure.exterior.coords))
            perimeter_points_rotated = affinity.rotate(perimeter_points, -mowangle, origin=(0, 0))
            perimeter_points_rotated = [(pt.x, pt.y) for pt in perimeter_points_rotated.geoms]
            perimeter_rotated = Polygon(perimeter_points_rotated)
            for exclusion in figure.interiors:
                exclusion_points = MultiPoint(list(exclusion.coords))
                exclusion_points_rotated = affinity.rotate(exclusion_points, -mowangle, origin=(0, 0))
                exclusion_points_rotated = [(pt.x, pt.y) for pt in exclusion_points_rotated.geoms]
                exclusion_rotated = Polygon(exclusion_points_rotated)
                perimeter_rotated = perimeter_rotated.difference(exclusion_rotated)
            figure_rotated = perimeter_rotated
            return figure_rotated
        return figure

def linemask(perimeter: Polygon, mowoffset: float) -> MultiLineString:
    if perimeter.is_empty:
        logger.info('Backend: Selection to small create empty linemask')
        linemask = MultiLineString()
        return linemask
    logger.info('Backend: Create line mask')
    bounds = perimeter.bounds
    offs = bounds[1]
    mask_coords = []
    mask_coords.append(((bounds[0]-10, bounds[1]),(bounds[2]+10, bounds[1])))
    while True:
        offs = offs + mowoffset
        if offs > bounds[3]:
            break
        mask_coords.append(((bounds[0]-10, offs),(bounds[2]+10, offs)))
    linemask = MultiLineString(mask_coords)
    lines = linemask.intersection(perimeter)
    return lines

def gotopoints(perimeter: Polygon, mowoffset: float) -> MultiPoint:
    logger.info('Backend: Create goto points')
    bounds = perimeter.bounds
    offsx = bounds[0]
    offsy = bounds[1]
    mask_coordsx = []
    mask_coordsy = []
    mask_coordsx.append(((bounds[0], bounds[1]-10),(bounds[0], bounds[3]+10)))
    mask_coordsy.append(((bounds[0]-10, bounds[1]),(bounds[2]+10, bounds[1])))
    while True:
        offsx = offsx + mowoffset
        offsy = offsy + mowoffset
        if offsy > bounds[3] and offsx > bounds[2]:
            break
        mask_coordsx.append(((offsx, bounds[1]-10),(offsx, bounds[3]+10)))
        mask_coordsy.append(((bounds[0]-10, offsy),(bounds[2]+10, offsy)))
    linemaskx = MultiLineString(mask_coordsx)
    linemasky = MultiLineString(mask_coordsy)
    points = linemaskx.intersection(linemasky)
    points = points.intersection(perimeter)
    return points

def areatomow(perimeter: Polygon, distancetoborder: int, mowoffset: float) -> Polygon:
    logger.info('Backend: Create area to mow')
    mowoffset = -mowoffset
    if distancetoborder == 0:
        area_to_mow = perimeter
    else: 
        area_to_mow = perimeter.buffer(distancetoborder*mowoffset, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
    return area_to_mow

def route(points: list) -> LineString:
    logger.info('Backend: Transform route to shapely figure')
    route_as_line = LineString(points)
    return route_as_line
