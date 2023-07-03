import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *

from . import map, cutedge, lines
from ..data import mapdata
from ..data.mapdata import current_map

def calc(parameters, start_pos: list()):
    logger.info('Backend: Planning route:')
    logger.info(parameters)
    logger.info('Rover start position: '+str(start_pos))
    if parameters.pattern == 'lines' or parameters.pattern == 'squares' or parameters.pattern == 'rings':
        start_pos = Point(start_pos)
        start_pos = map.turn(start_pos, parameters.angle)
        selected_area_turned = map.turn(mapdata.selected_perimeter, parameters.angle)
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
        selected_area_turned = map.turn(mapdata.selected_perimeter, parameters.angle+90)
        area_to_mow, border = map.border(selected_area_turned, parameters.distancetoborder, parameters.width)
        line_mask = map.linemask(area_to_mow, parameters.width)
        route2 = lines.calcroute(area_to_mow, border, line_mask, [], list(last_coord.coords), parameters, parameters.angle+90)
        route2 = map.turn(route2, -parameters.angle-90)
        route.extend(list(route2.coords))

    current_map.areatomow = round(mapdata.selected_perimeter.area)
    current_map.calc_route_preview(route) 