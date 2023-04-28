import logging
logger = logging.getLogger(__name__)

from shapely.geometry import *

def separate_perimeter(perimeter):
    edge_to_cut = []
    if perimeter.geom_type == 'MultiPolygon':
        for i in range(len(perimeter.geoms)):
            perimeter_pol_coords = list(perimeter.geoms[i].exterior.coords)
            perimeter_pol = Polygon(perimeter_pol_coords)
            if not perimeter_pol.is_empty:
                edge_to_cut.append(perimeter_pol) 
            for k in range(len(perimeter.geoms[i].interiors)):
                exclusion_pol_coords = list(perimeter.geoms[i].interiors[k].coords)
                exclusion_pol = Polygon(exclusion_pol_coords)
                if not exclusion_pol.is_empty:
                    edge_to_cut.append(exclusion_pol)          
        return edge_to_cut  
         
    elif perimeter.geom_type == 'Polygon':
        perimeter_pol_coords = list(perimeter.exterior.coords)
        perimeter_pol = Polygon(perimeter_pol_coords)
        if not perimeter_pol.is_empty:
            edge_to_cut.append(perimeter_pol) 
        for i in range(len(perimeter.interiors)):
            exclusion_pol_coords = list(perimeter.interiors[i].coords)
            exclusion_pol = Polygon(exclusion_pol_coords)
            if not exclusion_pol.is_empty:
                edge_to_cut.append(exclusion_pol)
        return edge_to_cut
    else:
        logger.error('Backend(cutedge.py): Beim Berechnen der Kantenroute entstand eine unbekannte Shapely Figur:' +perimeter.geom_type+'. Die Berechnung wurde abgebrochen')
        return -1  

def calcroute(perimeter, NUM_EDGE, MOW_OFFSET, START):
    logger.info('Backend: Calc route for cutedge')
    mowoffs = -MOW_OFFSET
    num_edge_per = min(NUM_EDGE, 2)
    start_coords = START
    route = []
    edges_pol = []

    ###Berechne die äußere Kante zum Mähen und füge die Strecke der Route zu###
    if num_edge_per != 0:
        ###Starte mit dem äußeren Perimeter###
        route = list(perimeter.exterior.coords)
        ###Entferne Duplikate###
        route = list(dict.fromkeys(route))
        first_coords = [min(route, key=lambda coord: (coord[0]-start_coords[0][0])**2 + (coord[1]-start_coords[0][1])**2)]
        first_coords_nr = route.index(first_coords[0])
        route = route[first_coords_nr:]+route[:first_coords_nr]
        route.append(route[0])
    
        ##Berechne die restlichen Kanten zum Mähen, füge die nicht der Route zu. Sollen mehrere Runden gedreht werden, so wird die Funktion auch so oft aufgerufen## 
        for i in range(len(perimeter.interiors)):
            edges_pol.append(Polygon(perimeter.interiors[i].coords))
        
        new_perimeter = perimeter
        for i in range(1, num_edge_per):
            new_perimeter = new_perimeter.buffer(mowoffs, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
            new_perimeter = new_perimeter.simplify(0.05, preserve_topology=False)
            edges_pol.extend(separate_perimeter(new_perimeter))

    else:
        route.append(START)
    
    logger.info('Backend: Route for cutedge complete')
    logger.debug('Cutedge route: '+str(len(route))+' points; figures to calculate: '+str(len(edges_pol)))
    return route, edges_pol