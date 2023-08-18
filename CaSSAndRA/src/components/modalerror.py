from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.comm import cmdlist
from src.backend.utils import debuglogger

okbuttonmapuploadfailed = dbc.Button('OK', id=ids.OKBUTTONMAPUPLOADFAILED, class_name='ms-auto', n_clicks=0)

mapuploadfailed = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle('Error')),
                            dbc.ModalBody('Map upload failed! Operation aborted.'),
                            dbc.ModalFooter(okbuttonmapuploadfailed)
                        ],
                        id=ids.MODALERRORMAPUPLOAD,
                        is_open=False,
                    )

@callback(Output(ids.MODALERRORMAPUPLOAD, 'is_open'),
          [Input(ids.INTERVAL, 'n_intervals'),
           Input(ids.OKBUTTONMAPUPLOADFAILED, 'n_clicks'),
           State(ids.MODALERRORMAPUPLOAD, 'is_open')])
def check_mapupload(n_intervals: int, bok_n_clicks: int, is_open: bool) -> bool:
    context = ctx.triggered_id
    if context == ids.INTERVAL:
        return cmdlist.cmd_failed
    if bok_n_clicks:
        cmdlist.cmd_failed = False
        return not is_open
    return is_open