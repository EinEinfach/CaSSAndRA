import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *
from shapely import affinity

def create(map: pd.DataFrame) -> Polygon:
    logger.info('Backend: Create a shapely figure from data frame')
    perimeter = map[map['type'] == 'perimeter']
    map = map[map['type'] != 'perimeter']
    map = map[map['type'] != 'way']
    map = map[map['type'] != 'dockpoints']
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
    logger.info('Backend: Turning shapely figure. Angle: {}'.format(-mowangle))
    figure_rotated = affinity.rotate(figure, -mowangle, origin=(0, 0))
    return figure_rotated

def linemask(perimeter: Polygon, mowoffset: float) -> MultiLineString:
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

def border(perimeter: Polygon, distancetoborder: int, mowoffset: float) -> list():
    logger.info('Backend: Create map borders and area to mow')
    mowoffset = -mowoffset
    border = perimeter
    if distancetoborder == 0:
        border = border.buffer(0.05, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
        return perimeter, border
    else: 
        for i in range(distancetoborder):
            perimeter = perimeter.buffer(mowoffset, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
        return perimeter, border

def route(points: list()) -> LineString():
    logger.info('Backend: Transform route to shapely figure')
    route_as_line = LineString(points)
    return route_as_line
"""
if __name__ == '__main__':
    test = Polygon(([0, 0], [0, 4], [4, 4], [4, 0]))
    gotopoints(test, 0.1)
"""