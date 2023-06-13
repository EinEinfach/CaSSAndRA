import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *

from . import map, cutedge, lines
from ..data import mapdata
from ..data.mapdata import current_map

def calc(mowoffset: float, mowangle: int, start_pos: list(), pattern: str()):
    logger.debug('Coverage path planning: mowoffset: '+str(mowoffset)+' mowangle: '+str(mowangle)+' startpos: '+str(start_pos)+' pattern: '+pattern)
    if pattern == 'lines' or pattern == 'squares' or pattern == 'rings':
        start_pos = Point(start_pos)
        start_pos = map.turn(start_pos, mowangle)
        selected_area_turned = map.turn(mapdata.selected_perimeter, mowangle)
        area_to_mow, border = map.border(selected_area_turned, mapdata.distancetoborder, mowoffset)
        route, edge_polygons = cutedge.calcroute(border, mapdata.distancetoborder, mowoffset, list(start_pos.coords))
        line_mask = map.linemask(area_to_mow, mowoffset)
        route = lines.calcroute(area_to_mow, border, line_mask, edge_polygons, route)
        route = map.turn(route, -mowangle)
        mapdata.distancetogo = round(route.length)
        route = list(route.coords)

    if pattern == 'squares':
        last_coord = route[-1]
        last_coord = Point(last_coord)
        last_coord = map.turn(last_coord, mowangle+90)
        selected_area_turned = map.turn(mapdata.selected_perimeter, mowangle+90)
        area_to_mow, border = map.border(selected_area_turned, mapdata.distancetoborder, mowoffset)
        line_mask = map.linemask(area_to_mow, mowoffset)
        route2 = lines.calcroute(area_to_mow, border, line_mask, [], list(last_coord.coords))
        route2 = map.turn(route2, -mowangle-90)
        mapdata.distancetogo = mapdata.distancetogo + round(route2.length)
        route.extend(list(route2.coords))

    current_map.areatomow = round(mapdata.selected_perimeter.area)
    current_map.calc_route_preview(route) 