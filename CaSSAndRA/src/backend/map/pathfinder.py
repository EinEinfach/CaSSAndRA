import logging
logger = logging.getLogger(__name__)

import networkx as nx
from shapely.geometry import *
from shapely import affinity
from shapely.ops import *
from dataclasses import dataclass

#local imports
from ..data.mapdata import current_map

@dataclass
class PathFinder:
    angle: int = 0
    perimeter: Polygon = Polygon()
    perimeter_points: MultiPoint = MultiPoint()
    G: nx.Graph = nx.Graph()
    Gnew: nx.Graph = nx.Graph()

    def create(self) -> None:
        self.perimeter = current_map.perimeter_polygon
        self.perimeter_points = current_map.perimeter_points
        self.G = current_map.astar_graph
        self.Gnew = current_map.astar_graph

    def check_direct_way(self, start, end) -> bool:
        way = LineString([start, end])
        if way.length <= 0.01:
            direct_way_possible = True
        else:
            direct_way_possible = way.within(self.perimeter)
        return direct_way_possible

    def add_edges(self, point: Point) -> None:
        nearest_point = nearest_points(point, self.perimeter)[1]
        if self.check_direct_way(list(point.coords)[0], list(nearest_point.coords)[0]):
            direct_way = LineString((list(point.coords)[0], list(nearest_point.coords)[0]))
            self.Gnew.add_edge(list(direct_way.coords)[0], list(direct_way.coords)[1], weight=direct_way.length)
        for possible_point in self.perimeter_points.geoms:
            if self.check_direct_way(list(point.coords)[0], list(possible_point.coords)[0]):
                direct_way = LineString((list(point.coords)[0], list(possible_point.coords)[0]))
                self.Gnew.add_edge(list(direct_way.coords)[0], list(direct_way.coords)[1], weight=direct_way.length)
            if self.check_direct_way(list(nearest_point.coords)[0], list(possible_point.coords)[0]):
                direct_way = LineString((list(nearest_point.coords)[0], list(possible_point.coords)[0]))
                self.Gnew.add_edge(list(direct_way.coords)[0], list(direct_way.coords)[1], weight=direct_way.length)
        return list(point.coords)

    def find_way(self, start: list(), goal: list()) -> list:
        start = affinity.rotate(Point(start), self.angle, origin=(0, 0))
        goal = affinity.rotate(Point(goal), self.angle, origin=(0, 0))
        logger.debug('Pathfinder start: '+str(list(start.coords)) +' goal: '+str(list(goal.coords)))
        self.add_edges(start)
        self.add_edges(goal)
        try:
            astar_path = nx.astar_path(self.Gnew, list(start.coords)[0], list(goal.coords)[0], heuristic=None, weight='weight') 
            logger.debug('Pathfinder found a way: '+str(list(path.coords)))
            path = LineString(astar_path)
            path = affinity.rotate(path, -self.angle, origin=(0, 0))
            del astar_path[0] #remove first point it is given by legacy route 
            return list(path.coords)
        except Exception as e:
            logger.warning('Pathfinder could not find a way. Action aborted')
            logger.debug(str(e))
            return list()

pathfinder = PathFinder()

