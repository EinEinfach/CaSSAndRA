from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from . import buttons
from src.backend.data import mapdata, saveddata
from src.backend.utils import switch

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
                            dbc.ModalHeader(dbc.ModalTitle('Warning')),
                            dbc.ModalBody('This will overwrite your current perimeter. Do you want to continue?'),
                            dbc.ModalFooter([
                                buttons.okbuttonoverwriteperimter,  
                            ] ),
                        ],
                        id=ids.MODALOVERWRITEPERIMETER,
                        is_open=False,
                    )

@callback(Output(ids.MODALOVERWRITEPERIMETER, 'is_open'),
          [Input(ids.BUTTONSAVEIMPORTEDPERIMETER, 'n_clicks'),
           Input(ids.OKBUTTONOVERWRITEPERIMTER, 'n_clicks'),
           State(ids.DROPDOWNSUNRAYIMPORT, 'value'),
           State(ids.MODALOVERWRITEPERIMETER, 'is_open')])
def overwrite_perimeter(bsp_n_clicks: int, bok_n_clicks, map_nr: str(), is_open: bool) -> bool:
    context = ctx.triggered_id
    if context == ids.OKBUTTONOVERWRITEPERIMTER:
        status = switch.perimeter(mapdata.imported, map_nr)
        if status == 0:
            saveddata.save('perimeter')
    if bsp_n_clicks or bok_n_clicks:
        return not is_open
    return is_open
