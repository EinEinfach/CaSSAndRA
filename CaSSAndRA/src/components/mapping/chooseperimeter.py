from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

from src.components import ids
from . import buttons
from src.backend.data import mapdata
from src.backend.data.mapdata import mapping_maps

chooseperimeter = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Select map'),
                        dbc.CardBody([
                            dcc.Dropdown(id=ids.DROPDOWNCHOOSEPERIMETER, className='m-1', searchable=False),
                            dbc.Container([
                                buttons.selectperimeter,
                                buttons.addnewperimeter,
                                buttons.renameperimeter,
                                buttons.removeperimeter,   
                                buttons.copyperimeter,
                                buttons.finishfigure,
                            ], fluid=True),                      
                        ]), 
                    ], className='text-center m-1 w-90')
                ])

@callback(Output(ids.DROPDOWNCHOOSEPERIMETER, 'options'),
          Output(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
          [Input(ids.OKBUTTONNEWPERIMETER, 'n_clicks'),
           Input(ids.OKBUTTONCOPYPERIMETER, 'n_clicks'),
           Input(ids.OKBUTTONREMOVEPERIMETER, 'n_clicks'),
           Input(ids.OKBUTTONFINISHMAPPING, 'n_clicks'),
           Input(ids.OKBUTTONRENAMEPERIMETER, 'n_clicks'),
           Input(ids.URLUPDATE, 'pathname'),
           State(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
           State(ids.DROPDOWNCHOOSEPERIMETER, 'options')])
def update_dropdown_chooseperimeter(boknp_nclicks: int, 
                                    bokcp_nclicks: int, 
                                    bokdp_nclicks: int, 
                                    bokfm_nclicks: int, 
                                    bokrp_nclicks: int,
                                    pathname: str,
                                    dropdown_val_state: str(), 
                                    dropdown_opt_state: list(),
                                    ) -> list():
    time.sleep(0.5)
    context = ctx.triggered_id
    try:
        options = mapping_maps.saved.name.unique()
        options.sort()
        value = dropdown_val_state
    except:
        options = []
        value = None
    if context == ids.OKBUTTONNEWPERIMETER or context == ids.OKBUTTONREMOVEPERIMETER:
        mapping_maps.init()
        value = None
    return options, value

