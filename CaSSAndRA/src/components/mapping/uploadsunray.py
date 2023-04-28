from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from src.components import ids
from src.backend.utils import file
from src.backend.data import mapdata
from . import buttons

uploadsunray = dcc.Upload(buttons.uploadsunrayfile, id=ids.UPLOADSUNRAYFILE)

@callback(Output(ids.MODALSUNRAYIMPORT, 'is_open'),
          Output(ids.MODALSUNRAYIMPORTTITLE, 'children'),
          Output(ids.MODALSUNRAYIMPORTBODY, 'children'),
          Output(ids.DROPDOWNSUNRAYIMPORT, 'options'),
          Output(ids.BUTTONSAVEIMPORTEDPERIMETER, 'disabled'),
          [Input(ids.UPLOADSUNRAYFILE, 'contents'),
           Input(ids.OKBUTTONSUNRAYIMPORT, 'n_clicks'),
           State(ids.MODALSUNRAYIMPORT, 'is_open')])
def upload_sunray_file(content: str(), bok_n_clicks: int, is_open: bool) -> list():
    title = ''
    body = ''
    disabled = True
    if mapdata.imported.empty:
        options = []
        disabled = True
    else:
        options = mapdata.imported.map_nr.unique()
        disabled = False
    context = ctx.triggered_id
    if content is not None:
        status = file.parse_sunray_file(content)
        if status == 0:
            title = 'Info'
            body = 'Import successfull'
            options = mapdata.imported.map_nr.unique()
            disabled = False
        else:
            title = 'Warning'
            body = 'Import failed'
    if context == ids.UPLOADSUNRAYFILE or bok_n_clicks:
        return not is_open, title, body, options, disabled
    return is_open, title, body, options, disabled