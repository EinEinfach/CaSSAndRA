from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data import mapdata

mowsettings = dbc.Modal([
                        dbc.ModalHeader(dbc.ModalTitle('Mow settings')),
                        dbc.ModalBody([
                            html.P(['pattern'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTPATTERNSTATE, 
                                options=[
                                    {'label': 'lines', 'value': 'lines'},
                                    {'label': 'squares', 'value': 'squares'},
                                    {'label': 'rings', 'value': 'rings'},
                                ],
                                value=mapdata.patternstatepage
                            ),
                            html.P(['width'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWOFFSETSTATE, 
                                      value=mapdata.mowoffsetstatepage, 
                                      type='number', 
                                      min=0, 
                                      max=1, 
                                      step=0.01, 
                                      size='sm'
                            ), 
                            html.P(['angle'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWOANGLESTATE, 
                                      value=mapdata.mowanglestatepage, 
                                      type='number', 
                                      min=0, 
                                      max=359, 
                                      step=1, 
                                      size='sm'
                            ),
                        ]),
                        dbc.ModalFooter(
                            dbc.Button('OK', id=ids.BUTTONOKINPUTMAPSETTINGS, className='ms-auto', n_clicks=0)
                        ),
                ],id=ids.MODALMOWSETTINGS, is_open=False,
                )

@callback(Output(ids.MODALMOWSETTINGS, 'is_open'),
          [Input(ids.BUTTONMOWSETTINGS, 'n_clicks'),
           Input(ids.BUTTONOKINPUTMAPSETTINGS, 'n_clicks'),
           State(ids.MODALMOWSETTINGS, 'is_open'),
           State(ids.INPUTPATTERNSTATE, 'value'),
           State(ids.INPUTMOWOFFSETSTATE, 'value'),
           State(ids.INPUTMOWOANGLESTATE, 'value')])
def toggle_modal(n_clicks_bms: int, n_clicks_bok: int,
                 modal_is_open: bool, pattern: str(),
                 mowoffset: float, mowangle: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKINPUTMAPSETTINGS:
        if pattern != 'lines' and pattern != 'squares' and pattern != 'rings':
            mapdata.patternstatepage = 'lines'
        else:
            mapdata.patternstatepage = pattern
        try:
            if 0.1 <= float(mowoffset) <= 1:
                mapdata.mowoffsetstatepage = float(mowoffset)
            else:
                mapdata.mowanglestatepage = 0.18
        except:
            mapdata.mowanglestatepage = 0.18   
        try:
            if 0 <= int(mowangle) < 360:
                mapdata.mowanglestatepage = int(mowangle)
            else:
                mapdata.mowanglestatepage = 0
        except:
            mapdata.mowanglestatepage = 0
            
    if n_clicks_bms or n_clicks_bok:
        return not modal_is_open
    return modal_is_open