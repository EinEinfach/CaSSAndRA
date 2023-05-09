from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from . import buttons
from src.backend.data import mapdata, saveddata
from src.backend.utils import switch
from src.backend.data.mapdata import current_map, mapping_maps

sunrayimportstatus = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle(id=ids.MODALSUNRAYIMPORTTITLE)),
                            dbc.ModalBody(id=ids.MODALSUNRAYIMPORTBODY),
                            dbc.ModalFooter([
                                buttons.okbuttonsunrayimport,  
                            ] ),
                        ],
                        id=ids.MODALSUNRAYIMPORT,
                        is_open=False,
                    )

overwriteperimter = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle('Info')),
                            dbc.ModalBody('Please give an unique name for new perimeter'),
                            dbc.ModalBody(dbc.Input(id=ids.INPUTPERIMETERNAME, type='text')),
                            dbc.ModalFooter([
                                buttons.okbuttonoverwriteperimter,  
                            ] ),
                        ],
                        id=ids.MODALOVERWRITEPERIMETER,
                        is_open=False,
                    )

figurefinished = dbc.Modal([
                            dbc.ModalHeader(dbc.ModalTitle('Info')),
                            dbc.ModalBody('Create new perimeter from scratch?'),
                            dbc.ModalFooter([
                                buttons.okbuttonfigurefinished,  
                            ] ),
                        ],
                        id=ids.MODALFIGUREFINISHED,
                        is_open=False,          
                )

selectperimeter = dbc.Modal([
                            dbc.ModalHeader(dbc.ModalTitle('Info')),
                            dbc.ModalBody('Continue with selected perimeter'),
                            dbc.ModalFooter([
                                buttons.okbuttonselectedperimeter,  
                            ] ),
                        ],
                        id=ids.MODALSELECTEDPERIMETER,
                        is_open=False,          
                )

@callback(Output(ids.MODALOVERWRITEPERIMETER, 'is_open'),
          [Input(ids.BUTTONSAVEIMPORTEDPERIMETER, 'n_clicks'),
           Input(ids.OKBUTTONOVERWRITEPERIMTER, 'n_clicks'),
           State(ids.DROPDOWNSUNRAYIMPORT, 'value'),
           State(ids.MODALOVERWRITEPERIMETER, 'is_open'),
           State(ids.INPUTPERIMETERNAME, 'value')])
def overwrite_perimeter(bsp_n_clicks: int, bok_n_clicks, map_nr: str(), 
                        is_open: bool, perimeter_name: str()) -> bool:
    context = ctx.triggered_id
    if context == ids.OKBUTTONOVERWRITEPERIMTER:
        mapping_maps.select_imported(map_nr)
        if mapping_maps.select_imported_status == 0:
            saveddata.save_perimeter(mapping_maps.saved, mapping_maps.selected_import, perimeter_name)
    if bsp_n_clicks or bok_n_clicks:
        return not is_open
    return is_open

@callback(Output(ids.MODALSELECTEDPERIMETER, 'is_open'),
          [Input(ids.BUTTONSELECTPERIMETER, 'n_clicks'),
           Input(ids.BUTTONREMOVEPERIMETER, 'n_clicks'),
           Input(ids.OKBUTTONSELECTEDPERIMETER, 'n_clicks'),
           State(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
           State(ids.MODALSELECTEDPERIMETER, 'is_open'),])
def selected_perimeter(bsp_n_clicks: int, brp_n_clicks, bok_n_clicks: int, 
                       selected_perimeter: str(), is_open: bool) -> list:
    context = ctx.triggered_id
    if selected_perimeter == None:
        return is_open
    selected = mapping_maps.saved[mapping_maps.saved['name'] == selected_perimeter] 
    if context == ids.OKBUTTONSELECTEDPERIMETER:
        current_map.perimeter = selected
        current_map.create(selected_perimeter)
    if bsp_n_clicks or bok_n_clicks or brp_n_clicks:
        return not is_open
    return is_open
