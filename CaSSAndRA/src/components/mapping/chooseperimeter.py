from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from src.components import ids
from . import buttons
from src.backend.data import mapdata
from src.backend.data.mapdata import mapping_maps

chooseperimeter = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Select map'),
                        dbc.CardBody([
                            dcc.Dropdown(id=ids.DROPDOWNCHOOSEPERIMETER, className='m-1'),
                            dbc.Container([
                                buttons.selectperimeter,
                                buttons.addnewperimeter,
                                buttons.copyperimeter,
                                buttons.removeperimeter,   
                                buttons.finishfigure
                            ], fluid=True),                      
                        ]), 
                    ], className='text-center m-1 w-90')
                ])

@callback(Output(ids.DROPDOWNCHOOSEPERIMETER, 'options'),
          Output(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
          [Input(ids.OKBUTTONOVERWRITEPERIMTER, 'n_clicks'),
           Input(ids.OKBUTTONNEWPERIMETER, 'n_clicks'),
           Input(ids.URLUPDATE, 'pathname'),
           State(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
           State(ids.DROPDOWNCHOOSEPERIMETER, 'options')])
def update_dropdown_chooseperimeter(bok_nclicks: int, pathname: str, bok2_nclicks: int, 
                                    dropdown_val_state: str(), dropdown_opt_state: list()) -> list():
    context = ctx.triggered_id
    try:
        options = mapping_maps.saved.name.unique()
        value = dropdown_val_state
    except:
        options = []
        value = None
    if context == ids.OKBUTTONNEWPERIMETER:
        value = None
        mapping_maps.init()
    return options, value

