import logging
logger = logging.getLogger(__name__)

from shapely.geometry import *
from shapely.ops import *

from ..data import mapdata

def calc_transit_lines (perimeter, mowoffset):
    ###Bestimme die Schnittgrenzen###
    bounds = perimeter.bounds

    ###Extrahiere y-Koordinate bei jedem Punkt für Perimeter und Exclusionen###
    if perimeter.geom_type == 'Polygon':
        y_coords = []
        for coord in list(perimeter.exterior.coords):
            y_coords.append(coord[1])
        for interior in perimeter.interiors:
            for coord in list(interior.coords):
                y_coords.append(coord[1])
    else:
        y_coords = []
        for perimeter in perimeter.geoms:
            for coord in list(perimeter.exterior.coords):
                y_coords.append(coord[1])
            for interior in perimeter.interiors:
                for coord in list(interior.coords):
                    y_coords.append(coord[1])

    ###Entferne Duplikate aus y_coords und sortiere in aufsteigender Reihenfolge###
    y_coords = list(dict.fromkeys(y_coords))
    y_coords.sort()

    ###Berechne die Schnittlinien mit dem Perimeter###
    intersection_lines_coords = []
    for y_coord in y_coords:
        intersection_lines_coords.append([(bounds[0], y_coord), (bounds[2], y_coord)])

    intersection_lines = MultiLineString(intersection_lines_coords)
    intersection_lines = intersection_lines.intersection(perimeter)

    ###Lege ein Dictionary an mit zusätzlichen Informationen an, die für die spätere Berechnung notwendig ist###
    transit_lines = dict()
    for i in range(len(intersection_lines.geoms)):
        try: 
            coord_1, coord_2 = zip(*list(intersection_lines.geoms[i].coords))
            line_level = (coord_2[1]-bounds[1])//mowoffset
            transit_lines[i] = [intersection_lines.geoms[i], coord_2[1], line_level, list(intersection_lines.geoms[i].coords)]
        except:
            pass

    return transit_lines

def calc_shortest_path(lines_to_go, perimeter_offs, lines_to_check, route, transit_lines):
    line_going_old = None
    line_going_nr_old = None
    possible_transit_lines_nr = []
    transit_line_coords_right = []
    transit_line_coords_left = []
    transit_polygon_coords = []
    y_coord = list(lines_to_go[lines_to_check[0]][0].coords)
    y_coord = y_coord[0][1]

    if route[-1][1] < y_coord:
        go_up = True
    else:
        go_up = False
    
    if go_up:
        possible_transit_lines_nr = [k for k, line in transit_lines.items() if route[-1][1] < line[1] < y_coord]
    else:
        possible_transit_lines_nr = [k for k, line in transit_lines.items() if route[-1][1] > line[1] > y_coord]
    
    for transit_line_nr in possible_transit_lines_nr:
        transit_line_coords_left.append(transit_lines[transit_line_nr][3][0])
        transit_line_coords_right.append(transit_lines[transit_line_nr][3][1])

    for possible_line_nr in lines_to_check:
        possible_line = lines_to_go[possible_line_nr]
        possible_line_coords = list(possible_line[0].coords)
        possible_way1 = LineString([route[-1], possible_line_coords[0]])
        possible_way2 = LineString([route[-1], possible_line_coords[1]])
        if possible_way1.covered_by(perimeter_offs) and possible_way2.covered_by(perimeter_offs):
            if possible_way1.length < possible_way2.length:
                line_going = possible_way1
                line_going_nr = possible_line_nr
            else:
                line_going = possible_way2
                line_going_nr = possible_line_nr

        elif possible_way1.covered_by(perimeter_offs):
            line_going = possible_way1
            transit_line_coords_right_tmp = transit_line_coords_right.copy()
            transit_polygon_coords = possible_line_coords
            transit_polygon_coords.append(route[-1])
            transit_polygon = Polygon(transit_polygon_coords)
            for transit_line_coord in transit_line_coords_right_tmp:
                transit_point = Point(transit_line_coord)
                if not transit_point.covered_by(transit_polygon):
                    transit_line_coords_right.remove(transit_line_coord)
            if len(transit_line_coords_right) != 0:
                transit_line_coords_right.append(route[-1])
                transit_line_coords_right.append(possible_line_coords[1]) 
                if go_up:  
                    transit_line_coords_right.sort(key=lambda x: x[1])
                else:
                    transit_line_coords_right.sort(key=lambda x: x[1], reverse=True)
                possible_way2 = LineString(transit_line_coords_right) 
                if possible_way2.covered_by(perimeter_offs) and possible_way2.length < possible_way1.length:
                    line_going = possible_way2
            line_going_nr = possible_line_nr

        elif possible_way2.covered_by(perimeter_offs):
            line_going = possible_way2
            transit_line_coords_left_tmp = transit_line_coords_left.copy()
            transit_polygon_coords = possible_line_coords
            transit_polygon_coords.append(route[-1])
            transit_polygon = Polygon(transit_polygon_coords)
            for transit_line_coord in transit_line_coords_left_tmp:
                transit_point = Point(transit_line_coord)
                if not transit_point.covered_by(transit_polygon):
                    transit_line_coords_left.remove(transit_line_coord)
            if len(transit_line_coords_left) != 0:
                transit_line_coords_left.append(route[-1])
                transit_line_coords_left.append(possible_line_coords[0])   
                if go_up:
                    transit_line_coords_left.sort(key=lambda x: x[1])
                else:
                    transit_line_coords_left.sort(key=lambda x: x[1], reverse=True)
                possible_way1 = LineString(transit_line_coords_left)
                if possible_way1.covered_by(perimeter_offs) and possible_way1.length < possible_way2.length:
                    line_going = possible_way1
            line_going_nr = possible_line_nr

        else:
            line_going = None
            line_going_nr = None
        try:
            if line_going.length <= line_going_old.length:
                line_going_old = line_going
                line_going_nr_old = line_going_nr
        except:
            if not line_going == None:
                line_going_old = line_going
                line_going_nr_old = line_going_nr
        
    return line_going_old, line_going_nr_old

def calc_shortest_path_edge(edges_to_cut, perimeter_offs, route):
    line_to_return = None
    line_to_excl = None
    edge_nr_to_return = None
    start_point = Point(route[-1])
    for edge_to_cut in edges_to_cut:
        near_point = nearest_points(edges_to_cut[edge_to_cut], start_point)
        line_to_excl = LineString([start_point, near_point[0]])
        if line_to_excl.covered_by(perimeter_offs) and line_to_return == None:
            line_to_return = line_to_excl
            edge_nr_to_return = edge_to_cut
        elif line_to_excl.covered_by(perimeter_offs) and line_to_excl.length < line_to_return.length:
            line_to_return = line_to_excl
            edge_nr_to_return = edge_to_cut
    
    return line_to_return, edge_nr_to_return

def put_route_together(line_going, lines_to_go):          
    line_to_go_nr = [k for k, line in lines_to_go.items() if line[3][0] == list(line_going.coords)[-1] or line[3][1] == list(line_going.coords)[-1]]
    coords_next_line = list(line_going.coords)
    line_level = lines_to_go[line_to_go_nr[0]][2]
    coords_next_line.extend(list(lines_to_go[line_to_go_nr[0]][0].coords))
    ###Entferne Duplikate###
    coords_next_line = list(dict.fromkeys(coords_next_line))
    
    return coords_next_line, line_to_go_nr, line_level

def put_edge_route_together(line_to_edge, edges_to_cut, edge_nr, perimeter_offs):
    coords_next_line = []
    line_coords = list(line_to_edge.coords)
    line_end_coords = line_coords[1]
    edge_coords = list(edges_to_cut[edge_nr].exterior.coords)
    ###Entferne Duplikate###
    edge_coords = list(dict.fromkeys(edge_coords))
    start_coords = min(edge_coords, key=lambda coord: (coord[0]-line_end_coords[0])**2 + (coord[1]-line_end_coords[1])**2)
    start_coords_nr = edge_coords.index(start_coords)
    edge_route = edge_coords[start_coords_nr:] + edge_coords[:start_coords_nr]
    edge_line = LineString([edge_route[0], edge_route[-1]])
    #if not line_to_edge.touches(edge_line):
        #edge_route = edge_coords[start_coords_nr+1:] + edge_coords[:start_coords_nr+1]    
    edge_route.append(line_end_coords)
    coords_next_line.extend(line_coords)
    coords_next_line.extend(edge_route)

    return coords_next_line, edge_nr

def check_for_lines_in_range(lines_to_go, perimeter_offs, lines_to_check, current_line_nr, route):
    lines_in_range_cnt = 0
    line_for_return = None
    line_nr = None
    new_lines_nr = []
    new_lines = []
    line_coords = list(lines_to_go[current_line_nr][0].coords)
    line_coords.sort(key=lambda x: x[0])
    for line in lines_to_check:
        line_coords_to_check = list(lines_to_go[line][0].coords)
        new_line1 = LineString([(line_coords_to_check[0][0], line_coords[0][1]), line_coords_to_check[0]])
        new_line2 = LineString([(line_coords_to_check[1][0], line_coords[0][1]), line_coords_to_check[1]])
        if new_line1.covered_by(perimeter_offs): 
            new_line = LineString([route[-1], (line_coords_to_check[0][0], line_coords[0][1])])
            if new_line.covered_by(perimeter_offs):
                lines_in_range_cnt += 1
                new_lines.append(new_line) 
                new_lines_nr.append(line) 
        elif new_line2.covered_by(perimeter_offs):
            new_line = LineString([route[-1], (line_coords_to_check[1][0], line_coords[0][1])])
            if new_line.covered_by(perimeter_offs):
                lines_in_range_cnt += 1
                new_lines.append(new_line)
                new_lines_nr.append(line) 
    if len(new_lines) != 0:
        line_for_return = new_lines[0]
        line_nr = new_lines_nr[0]
        for i in range(len(new_lines)):
            if new_lines[i].length < line_for_return.length:
                line_for_return = new_lines[i]
                line_nr = new_lines_nr[i]
                
    return lines_in_range_cnt, line_for_return, line_nr


def calcroute(perimeter, borders, line_mask, edges_pol, route, parameters):
    MAX_NUM_CHECK = 50

    perimeter_offs = borders.buffer(0.05, resolution=16, join_style=2, mitre_limit=1, single_sided=True)
    transit_lines = calc_transit_lines(perimeter_offs, parameters.width)
    ################################################################################################

    ###Berechne die Mählinien, die abgefahren werden müssen###
    result_lines = line_mask.intersection(perimeter)
    ###Extrahiere neue Koordinaten und sortiere nach Y-Koordinate in aufsteigender Reihenfolge###
    result_lines_coords = []
    ##Prüfe, ob für das Extrahieren auch ein MultiLineString vorliegt, wenn nicht dann mit except weiter##
    try: 
        for line in result_lines.geoms:
            ##Bei der Extraktion filtere einzlne Punke (ohne Linienbezug) aus, und duppliziere die Koordinate, damit der Punkt sich wie eine Linie verhält##
            if len(list(line.coords)) == 1:
                coords = list(line.coords)
                coords.extend(coords)
                result_lines_coords.append(coords)
            ##Bei der Extraktoin sind zwei Koordinaten entstanden, die eine Linie bilden (wie erwartet)##
            else:
                result_lines_coords.append(list(line.coords))
    ##Beim Versuch Daten zu extrahieren, liegt kein MultiLineString vor, versuche mit Exception weiter (LineString? Leer?)##
    except:
        ##Prüfe, ob die Extraktion möglich ist (ist result_lines leer?)##
        if not result_lines.is_empty:
            line = result_lines
            ##Wenn line ein einzelner Punkt ist, dann duppliziere die Koordinate, damit der Punkt sich wie eine Linie verhält##
            if len(list(line.coords)) == 1:
                coords = list(line.coords)
                coords.extend(coords)
                result_lines_coords.append(coords)
            ##line ist ein LineString (wie erwartet)##
            else:
                result_lines_coords.append(list(line.coords))
        ##Extraktion nicht möglich, result_lines ist leer, breche ab und gebe leeres Element zurück
        else:
            return None, line_mask
    ###Sortiere die Koordinaten nach Y-Koordiante und bilde einen neuen MultiLineString###
    result_lines_coords.sort(key=lambda x: x[0][1])
    result_lines = MultiLineString(result_lines_coords)
    #######################################################################################

    ###Lege einen edge_to_cut-Dictionary mit zusätzlichen Informationen an, die für die Berechnung notwendig sind###
    edges_to_cut = dict()
    for i in range(len(edges_pol)):
        edges_to_cut[i] = edges_pol[i]

    ###Lege einen Mählinien-Dictionary an mit zusätzlichen Informationen an, die für die Berechnung der Route notwendig ist###
    line_level = 0
    coord_1, coord_2 = zip(*list(result_lines.geoms[0].coords))
    coord_y_old = coord_2[0]
    lines_to_go = dict()
    for i in range(len(result_lines.geoms)):
        coord_1, coord_2 = zip(*list(result_lines.geoms[i].coords))
        if coord_2[0] > coord_y_old:
            line_level += 1
        lines_to_go[i] = [result_lines.geoms[i], coord_2[0], line_level, list(result_lines.geoms[i].coords)]
        coord_y_old = coord_2[0]

    #route = []
    line_for_return = []
    ###Lege eine Kopie der lines_to_go. Wird benötigt bei der Transitrouten Berechnung###
    lines_to_go_cpy = lines_to_go.copy()
    ###Extrahiere Koordinaten der Transitlinien. Wird benötigt um mögliche Übergänge zwischen den Liniene zu vereinfachen###
    #transit_lines_coords = []
    #for line in transit_lines:
        #transit_lines_coords.append(list(transit_lines[line][0].coords))
   

    ###Lege fest wo gestartet werden soll und spure in die erste Mow-Linie oder Mähkante ein ###
    possible_start_line_nr1 = min(lines_to_go, key=lambda line: (lines_to_go[line][3][0][0]-route[-1][0])**2 + (lines_to_go[line][3][0][1]-route[-1][1])**2)
    possible_start_line_nr2 = min(lines_to_go, key=lambda line: (lines_to_go[line][3][1][0]-route[-1][0])**2 + (lines_to_go[line][3][1][1]-route[-1][1])**2)
    possible_start_nr = [possible_start_line_nr1, possible_start_line_nr2]
    ###No mow border selected deliver route with just start point, leads to problems if it outside perimeter
    if len(route) == 1:
        route = []
        route.append(lines_to_go[possible_start_line_nr1][0].coords[0])
    line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, possible_start_nr, route, transit_lines)
    line_to_edge, edge_nr = calc_shortest_path_edge(edges_to_cut, perimeter_offs, route)
    if line_to_edge != None and line_to_edge.length < line_going.length:
        coords_next_line, edge_nr = put_edge_route_together(line_to_edge, edges_to_cut, edge_nr, perimeter_offs)
        route.extend(coords_next_line)
        edges_to_cut.pop(edge_nr)
        line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, possible_start_nr, route, transit_lines)
    coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)
    route.extend(coords_next_line)
    ###Debug: Manuelle Vorgabe zur Startlinie###
    ###line_going_nr = 200
    ###line_going = lines_to_go[line_going_nr]
    ###line_coord = list(line_going[0].coords)
    ###line_coord.sort(key=lambda x: x[0])
    ###line_level = line_going[2]
    ###route.extend(line_coord)
    
    line_gone_nr = line_going_nr   
    line_going = None

    lines_with_one_level_under = [k for k, line in lines_to_go.items() if line[2] == line_level-1]
    lines_with_same_level = [k for k, line in lines_to_go.items() if line[2] == line_level]
    lines_with_one_level_over = [k for k, line in lines_to_go.items() if line[2] == line_level+1]

    ###Debug###
    while_cnt = 0
    while_1 = 0
    while_21 = 0
    while_22 = 0
    while_31 = 0
    while_32 = 0
    while_4 = 0
    while_5 = 0
    while_excl1 = 0
    while_excl2 = 0
    while_excl2 = 0
    ###########

    while True:
        ###Debug##
        # logger.debug(str(len(lines_to_go)))
        # logger.debug(str(while_cnt)+' '+str(while_1)+' '+str(while_21)+' '+str(while_22)+' '+str(while_31)+' '+str(while_32)+' '+str(while_4)+' '+str(while_5))
        # logger.debug(str(len(route))+' '+str(route[-1]))

        ##########

        line_to_edge, edge_nr = calc_shortest_path_edge(edges_to_cut, perimeter_offs, route)
        if line_to_edge != None and line_to_edge.length < 2*0.18:
            coords_next_line, edge_nr = put_edge_route_together(line_to_edge, edges_to_cut, edge_nr, perimeter_offs)
            start_to_edge = route[-1]
            route.extend(coords_next_line)
            edges_to_cut.pop(edge_nr)
            line_to_edge = None
            line_to_edge, edge_nr = calc_shortest_path_edge(edges_to_cut, perimeter_offs, route)
            if line_to_edge != None and line_to_edge.length < 2*0.18:
                coords_next_line, edge_nr = put_edge_route_together(line_to_edge, edges_to_cut, edge_nr, perimeter_offs)  
                route.extend(coords_next_line)
                edges_to_cut.pop(edge_nr)
                line_to_edge = None  
            route.append(start_to_edge)
            
            ###Debug###
            while_excl1 += 1
            ###########
        
        lines_in_range_cnt_under, line_in_range, line_nr = check_for_lines_in_range(lines_to_go, perimeter_offs, lines_with_one_level_under, line_gone_nr, route)
        lines_in_range_cnt_over, line_in_range, line_nr = check_for_lines_in_range(lines_to_go, perimeter_offs, lines_with_one_level_over, line_gone_nr, route)
        if lines_in_range_cnt_under < 2 and lines_in_range_cnt_over < 2:
            lines_to_go.pop(line_gone_nr)
            try:
                line_for_return.remove(line_gone_nr)
            except:
                pass
        else:
            line_for_return.append(line_gone_nr)
            ###Entferne Duplikate###
            line_for_return = list(dict.fromkeys(line_for_return))

        ###Berechnung abgeschlossen, wenn alle Linien abgefahren wurden###
        if len(lines_to_go) == 0:
            logger.info('Backend: Route wurde vollständig berechnet')
            break 

        ###Es sind Mählinien unter der aktuellen Mählinie vorhanden.###
        if len(lines_with_one_level_under) != 0:
            ###Ist ein direkter Wechsel möglich?###
            line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, lines_with_one_level_under, route, transit_lines)
            ###Direkter Wechsel in die Mählinie drunter nicht möglich (Anderer Polygon? Entfernung zu weit?) Prüfe, ob die x-Koordinate im Range ist###
            if not line_going:
                lines_in_range_cnt, line_in_range, line_nr = check_for_lines_in_range(lines_to_go_cpy, perimeter_offs, lines_with_one_level_under, line_gone_nr, route)
                ###Keine Linien in Range, wechsel auf untere Linie nicht möglich
                if lines_in_range_cnt == 0:
                    pass
                else:
                    pass
                    #line_going = line_in_range
                    #coords_next_line = list(line_going.coords)
                    #coords_next_line.append(route[-1])
                    ###Entferne Duplikate###
                    #coords_next_line = list(dict.fromkeys(coords_next_line))
                    #route.extend(coords_next_line)
                    #line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, lines_with_one_level_under, route, transit_lines)
                    #coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)
                    #route.extend(coords_next_line)
            ###Mählinie drunter ist nicht im Range der x-Koordinate. Gehe dann die Mählinie drüber###
            else:
                coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)
                route.extend(coords_next_line)              

                ###Debug###
                while_1 += 1
                ###########

        ###Es sind Mählinien über der aktuellen Mählinie vorhanden und vorherige Berechnung nicht erfolgreich, oder nicht stattgefunden. Wechsel möglich?###
        if len(lines_with_one_level_over) != 0 and line_going == None:
            line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, lines_with_one_level_over, route, transit_lines)
            ###Wechsel in die Mählinie drüber nicht möglich (Anderer Polygon? Entfernung zu weit?) Prüfe, ob die x-Koordinate im Range ist###
            if not line_going:
                lines_in_range_cnt, line_in_range, line_nr = check_for_lines_in_range(lines_to_go_cpy, perimeter_offs, lines_with_one_level_over, line_gone_nr, route)
                ###Keine Linien in Range, wechsel auf obere Linie nicht möglich
                if lines_in_range_cnt == 0:
                    pass
                else:
                    line_going = line_in_range
                    coords_next_line = list(line_going.coords)
                    coords_next_line.append(route[-1])
                    ###Entferne Duplikate###
                    coords_next_line = list(dict.fromkeys(coords_next_line))
                    route.extend(coords_next_line)
                    line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, lines_with_one_level_over, route, transit_lines)
                    coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)
                    route.extend(coords_next_line)

                    ###Debug###
                    while_21 += 1
                    ###########
            else:
                coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)
                route.extend(coords_next_line)

                ###Debug###
                while_22 += 1
                ###########

        #################Don't use, dead lock possible################
        ###Es sind keine direkte Übergänge, weder nach oben, noch nach unten möglich. Prüfe die Rückkehr über die gespeicherte Route###
        # if len(line_for_return) != 0 and line_going == None:
        #     line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, line_for_return, route, transit_lines)
        #     ###Wechsel über die gespeicherte Route nicht möglich (Sackgasse im konkaven Polygon?), ist die Rückkehrlinie in Range?###
        #     if not line_going:
        #         lines_in_range_cnt, line_in_range, line_nr = check_for_lines_in_range(lines_to_go_cpy, perimeter_offs, [line_gone_nr], line_for_return[-1], route)
        #         if lines_in_range_cnt == 0:
        #             pass
        #         else:
        #             line_going = line_in_range
        #             line_going_nr = line_for_return[-1]
        #             coords_next_line = list(line_going.coords)
        #             coords_next_line.append(route[-1])
        #             ###Entferne Duplikate###
        #             coords_next_line = list(dict.fromkeys(coords_next_line))
        #             route.extend(coords_next_line)  
        #             line_level = lines_to_go[line_for_return[-1]][2]
        #             line_for_return.remove(line_going_nr)

        #             ###Debug###
        #             while_31 += 1
        #             ###########
        #     else:
        #         #coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)
        #         coords_next_line = list(line_going.coords)
        #         coords_next_line.append(route[-1])
        #         ###Entferne Duplikate###
        #         coords_next_line = list(dict.fromkeys(coords_next_line))
        #         route.extend(coords_next_line)   
        #         line_level = lines_to_go[line_going_nr][2]  
        #         line_for_return.remove(line_going_nr)  

        #         ###Debug###
        #         while_32 += 1
        #         ###########
        #######################################################################

        ###Prüfe ob der Übergang zur Exclusion möglich ist, wenn ja, dann geh zur Exclusion, komme aber nicht wieder###
        if line_to_edge != None and line_to_edge.length < 6*0.18 and line_going == None:
            coords_next_line, edge_nr = put_edge_route_together(line_to_edge, edges_to_cut, edge_nr, perimeter_offs)
            start_to_edge = route[-1]
            route.extend(coords_next_line)
            edges_to_cut.pop(edge_nr)
            line_to_edge = None
            line_to_edge, edge_nr = calc_shortest_path_edge(edges_to_cut, perimeter_offs, route)
            if line_to_edge != None and line_to_edge.length < 2*0.18:
                coords_next_line, edge_nr = put_edge_route_together(line_to_edge, edges_to_cut, edge_nr, perimeter_offs)  
                route.extend(coords_next_line)
                edges_to_cut.pop(edge_nr)
                line_to_edge = None  
            #route.append(start_to_edge)
             
            ###Debug###
            while_excl2 += 1
            ###########

        ###Es sind keine Linien drüber oder drunter mehr enthalten, aber nicht alle Wege abgefahren, versuche einen Weg zu finden zu der Linie mit dem nächstniedrgem Level###
        if line_going == None: #len(lines_with_one_level_over) == 0 and len(lines_with_one_level_under) == 0:
            
            line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, list(lines_to_go.keys())[:MAX_NUM_CHECK], route, transit_lines)
            ###Wechsel über die Linie mit dem nächstniedrgem Level nicht möglich, versuche über die Transitlinien###
            if line_going == None:
                pass
                #possible_transit_line_nr, possible_transit_line = min(transit_lines.items(), key=lambda x: abs(lines_to_go[min(lines_to_go.keys())][2] - x[1][2]))
                #lines_with_same_level = [k for k, line in transit_lines.items() if line[2] == transit_lines[possible_transit_line_nr][2]]
                #line_going, line_going_nr = calc_shortest_path(transit_lines, perimeter_offs, lines_with_same_level, route, transit_lines)
                #if line_going == None:
                    #print("Debug: Fehler keine Route über Transitlinien gefunden")
                #else:
                    #coords_next_line = list(line_going.coords)
                    #coords_next_line.append(route[-1])
                    ###Entferne Duplikate###
                    #coords_next_line = list(dict.fromkeys(coords_next_line))
                    #line_level = transit_lines[line_going_nr][2]
                    #route.extend(coords_next_line)  
            else:
                coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)
                route.extend(coords_next_line)

                ###Debug###
                while_4 += 1
                ###########

        ###Alle Versuche sind gescheitert, prüfe ob es eine Linie über Rand erreichbar ist###
        if line_going == None:
            perimeter_coords = list(perimeter_offs.exterior.coords)
            ###Entferne Duplikate###
            perimeter_coords = list(dict.fromkeys(perimeter_coords))
            start_coords = [min(perimeter_coords, key=lambda coord: (coord[0]-route[-1][0])**2 + (coord[1]-route[-1][1])**2)]
            start_coords_nr = perimeter_coords.index(start_coords[0])
            possible_way = LineString([route[-1], perimeter_coords[start_coords_nr]])
            
            try_cnt = 1
            while not possible_way.covered_by(perimeter_offs):
                start_coords_nr = start_coords_nr - 1
                try:
                    possible_way = LineString([route[-1], perimeter_coords[start_coords_nr]])
                except Exception as e:
                #if start_coords == perimeter_coords[start_coords_nr]:
                    logger.debug('calc lines: Kein direkter Übergang zur Perimetergrenze möglich. Setze eine Koordinate zurück')
                    route.append(route[-2*try_cnt])
                    start_coords = [min(perimeter_coords, key=lambda coord: (coord[0]-route[-1][0])**2 + (coord[1]-route[-1][1])**2)]
                    start_coords_nr = perimeter_coords.index(start_coords[0])
                    possible_way = LineString([route[-1], perimeter_coords[start_coords_nr]])
                    try_cnt += 1
              
            perimeter_coords = perimeter_coords[start_coords_nr:]+perimeter_coords[:start_coords_nr]
            perimeter_coords.append(perimeter_coords[0])
            perimeter_coords_rev = perimeter_coords[::-1]
            for i in range(1, len(perimeter_coords)):
                route_tmp = perimeter_coords[:i+1]
                line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, list(lines_to_go.keys())[:MAX_NUM_CHECK], route_tmp, transit_lines)
                if line_going == None:
                    pass
                else:
                    route_tmp.remove(route_tmp[-1]) 
                    route.extend(route_tmp) 
                    coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)  
                    route.extend(coords_next_line) 
                    break

                route_tmp = perimeter_coords_rev[:i+1]
                line_going, line_going_nr = calc_shortest_path(lines_to_go, perimeter_offs, list(lines_to_go.keys())[:MAX_NUM_CHECK], route_tmp, transit_lines)
                if line_going == None:
                    pass
                else:
                    route_tmp.remove(route_tmp[-1]) 
                    route.extend(route_tmp) 
                    coords_next_line, line_to_go_nr, line_level = put_route_together(line_going, lines_to_go)  
                    route.extend(coords_next_line) 
                    break
            
            ###Debug###
            while_5 += 1
            ###########
                
        ###Berechne die verfügbaren Linien###
        lines_with_one_level_under = [k for k, line in lines_to_go.items() if line[2] == line_level-1]
        lines_with_same_level = [k for k, line in lines_to_go.items() if line[2] == line_level]
        lines_with_one_level_over = [k for k, line in lines_to_go.items() if line[2] == line_level+1]
        line_gone_nr = line_going_nr
        ###Entferne Rückkehrroute als eine Linie zum abfahren###
        if len(line_for_return) != 0:
            for line in line_for_return:
                try:
                    lines_with_one_level_under.remove(line)
                except:
                    pass
                try:
                    lines_with_one_level_over.remove(line)
                except:
                    pass

        if line_going == None:
            logger.warning('Backend: Fehler! Route konnte nicht vollständig berechnet werden')
            break

        line_going = None
        ###Debug###
        while_cnt += 1
    route_shapely = LineString(route) 
    #logger.debug('Anzahl While-Aufrufe: '+str(while_cnt))  
    #length = route_shapely.length
    #logger.debug('Länge der Route: '+str(round(length, 2)), 'm. Anzahl der Punkte: ' +str(len(route)))  
    #logger.debug('Debug: 1: ', while_1,' 2.1: ', while_21, ' 2.2: ', while_22, ' 3.1: ', while_31, ' 3.2: ', while_32, ' 4: ', while_4, ' 5: ', while_5)
    #logger.debug('Debug: 1: ', while_excl1, ' 2: ', while_excl2)
    return route_shapely