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
                            dcc.Dropdown(id=ids.DROPDOWNCHOOSEPERIMETER, className='m-1'),
                            dbc.Container([
                                buttons.selectperimeter,
                                buttons.addnewperimeter,
                                buttons.renameperimeter,
                                buttons.finishfigure,
                                buttons.removeperimeter,   
                                buttons.copyperimeter,
                            ], fluid=True),                      
                        ]), 
                    ], className='text-center m-1 w-90')
                ])

@callback(Output(ids.DROPDOWNCHOOSEPERIMETER, 'options'),
          Output(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
          [Input(ids.OKBUTTONNEWPERIMETER, 'n_clicks'),
          Input(ids.MODALCOPYPERIMETER, 'is_open'),
          Input(ids.MODALREMOVEPERIMETER, 'is_open'),
          Input(ids.MODALFINISHMAPPING, 'is_open'),
          Input(ids.MODALRENAMEPERIMETER, 'is_open'),
          Input(ids.URLUPDATE, 'pathname'),
          State(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
          State(ids.DROPDOWNCHOOSEPERIMETER, 'options')])
def update_dropdown_chooseperimeter(boknp_nclicks: int, 
                                    cp_isopen: bool, 
                                    dp_isopen: bool, 
                                    sp_isopen: bool, 
                                    rp_isopen: bool,
                                    pathname: str,
                                    dropdown_val_state: str(), 
                                    dropdown_opt_state: list(),
                                    ) -> list():
    time.sleep(0.5)
    context = ctx.triggered_id
    try:
        options = mapping_maps.saved.name.unique()
        value = dropdown_val_state
    except:
        options = []
        value = None
    if context == ids.OKBUTTONNEWPERIMETER or context == ids.OKBUTTONREMOVEPERIMETER:
        value = None
        mapping_maps.init()
    return options, value

