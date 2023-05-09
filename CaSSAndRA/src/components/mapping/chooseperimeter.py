from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from src.components import ids
from . import buttons
from src.backend.data import mapdata
from src.backend.data.mapdata import mapping_maps

chooseperimeter = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Saved perimeters'),
                        dbc.CardBody([
                            dcc.Dropdown(id=ids.DROPDOWNCHOOSEPERIMETER, className='m-1'),
                            dbc.Row([
                                dbc.Col(buttons.selectperimeter),
                                dbc.Col(buttons.removeperimeter)   
                            ], justify='center'),                      
                        ]), 
                    ], className='text-center m-1 w-90')
                ])

@callback(Output(ids.DROPDOWNCHOOSEPERIMETER, 'options'),
          Output(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
          [Input(ids.OKBUTTONOVERWRITEPERIMTER, 'n_clicks'),
           Input(ids.INTERVAL, 'n_intervals'),
           State(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
           State(ids.DROPDOWNCHOOSEPERIMETER, 'options')])
def update_dropdown_chooseperimeter(bok_nclicks: int, n_intervals: int, 
                                    dropdown_val_state: str(), dropdown_opt_state: list()) -> list():
    # context = ctx.triggered_id
    # if context == ids.INTERVAL:
    #     return dropdown_opt_state, dropdown_val_state
    try:
        options = mapping_maps.saved.name.unique()
        value = dropdown_val_state
    except:
        options = []
        value = None
    return options, value

