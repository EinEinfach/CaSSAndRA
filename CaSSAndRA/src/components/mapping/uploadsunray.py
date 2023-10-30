from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from src.components import ids
from src.backend.data.mapdata import mapping_maps
from . import buttons

uploadsunray = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Import map'),
                        dbc.CardBody([
                            dcc.Dropdown(id=ids.DROPDOWNSUNRAYIMPORT, className='m-1', searchable=False),
                            dbc.Row([
                                dbc.Col(dcc.Upload(buttons.uploadsunrayfile, id=ids.UPLOADSUNRAYFILE)),
                                dbc.Col(buttons.saveimportedperimeter)   
                            ], justify='center'),
                                                  
                        ]), 
                    ], className='text-center m-1 w-90')
                ])


@callback(Output(ids.MODALSUNRAYIMPORT, 'is_open'),
          Output(ids.MODALSUNRAYIMPORTTITLE, 'children'),
          Output(ids.MODALSUNRAYIMPORTBODY, 'children'),
          Output(ids.DROPDOWNSUNRAYIMPORT, 'options'),
          Output(ids.BUTTONSAVEIMPORTEDPERIMETER, 'disabled'),
          Output(ids.DROPDOWNSUNRAYIMPORT, 'value'),
          [Input(ids.UPLOADSUNRAYFILE, 'contents'),
           #Input(ids.OKBUTTONSUNRAYIMPORT, 'n_clicks'),
           State(ids.MODALSUNRAYIMPORT, 'is_open')])
def upload_sunray_file(content: str(), 
                       #bok_n_clicks: int, 
                       is_open: bool
                       ) -> list():
    title = ''
    body = ''
    disabled = True
    if mapping_maps.imported.empty:
        options = []
        value = None
        disabled = True
    else: 
        options = mapping_maps.imported.map_nr.unique()
        value = options[0]
        disabled = False
    context = ctx.triggered_id
    if content is not None:
        mapping_maps.import_sunray(content)
        if mapping_maps.import_status == 0:
            title = 'Info'
            body = 'Import successfull'
            options = mapping_maps.imported.map_nr.unique()
            disabled = False
        else:
            title = 'Warning'
            body = 'Import failed'
    if context == ids.UPLOADSUNRAYFILE and title != '':# or bok_n_clicks:
        return True, title, body, options, disabled, value
    return False, title, body, options, disabled, value