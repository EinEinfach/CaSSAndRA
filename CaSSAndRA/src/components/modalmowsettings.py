from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data.cfgdata import pathplannercfgstate

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
                                value=pathplannercfgstate.pattern
                            ),
                            html.P(['width'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWOFFSETSTATE, 
                                      value=pathplannercfgstate.width, 
                                      type='number', 
                                      min=0, 
                                      max=1, 
                                      step=0.01, 
                                      size='sm'
                            ), 
                            html.P(['angle'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWOANGLESTATE, 
                                      value=pathplannercfgstate.angle, 
                                      type='number', 
                                      min=0, 
                                      max=359, 
                                      step=1, 
                                      size='sm'
                            ),
                            html.P(['distance to border'], className='mb-0'),
                            dbc.Input(id=ids.INPUTDISTANCETOBORDERSTATE, 
                                      value=pathplannercfgstate.distancetoborder, 
                                      type='number', 
                                      min=0, 
                                      max=5, 
                                      step=1, 
                                      size='sm'
                            ),
                            html.P(['mow area'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTMOWAREASTATE, 
                                options=[
                                    {'label': 'yes', 'value': 'yes'},
                                    {'label': 'no', 'value': 'no'}
                                ],
                                value=pathplannercfgstate.mowarea
                            ),
                            html.P(['mow cut edge border (rounds)'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWCUTEDGEBORDERSTATE, 
                                      value=pathplannercfgstate.mowborder, 
                                      type='number', 
                                      min=0, 
                                      max=6, 
                                      step=1, 
                                      size='sm'
                            ),
                            html.P(['mow cut edge exclusion'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTMOWCUTEDGEEXCLUSIONSTATE, 
                                options=[
                                    {'label': 'yes', 'value': 'yes'},
                                    {'label': 'no', 'value': 'no'}
                                ],
                                value=pathplannercfgstate.mowexclusion
                            ),
                            html.P(['mow cut edge border in ccw'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTMOWCUTEDGEBORDERCCWSTATE, 
                                options=[
                                    {'label': 'yes', 'value': 'yes'},
                                    {'label': 'no', 'value': 'no'}
                                ],
                                value=pathplannercfgstate.mowborderccw
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
           State(ids.INPUTMOWOANGLESTATE, 'value'),
           State(ids.INPUTDISTANCETOBORDERSTATE, 'value'),
           State(ids.INPUTMOWAREASTATE, 'value'),
           State(ids.INPUTMOWCUTEDGEBORDERSTATE, 'value'),
           State(ids.INPUTMOWCUTEDGEEXCLUSIONSTATE, 'value'),
           State(ids.INPUTMOWCUTEDGEBORDERCCWSTATE, 'value')])
def toggle_modal(n_clicks_bms: int, n_clicks_bok: int,
                 modal_is_open: bool, pattern: str(),
                 mowoffset: float, mowangle: int,
                 distancetoborder: int, mowarea: str,
                 mowborder: str, mowexclusion: str,
                 mowborderccw: str) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKINPUTMAPSETTINGS:
        if pattern != 'lines' and pattern != 'squares' and pattern != 'rings':
            pathplannercfgstate.pattern = 'lines'
        else:
            pathplannercfgstate.pattern = pattern
        if mowoffset != None:
            pathplannercfgstate.width = mowoffset
        if mowangle != None:
            pathplannercfgstate.angle = mowangle
        if distancetoborder != None:
            pathplannercfgstate.distancetoborder = distancetoborder
        pathplannercfgstate.mowarea = mowarea
        pathplannercfgstate.mowborder = mowborder
        pathplannercfgstate.mowexclusion = mowexclusion
        pathplannercfgstate.mowborderccw = mowborderccw
            
    if n_clicks_bms or n_clicks_bok:
        return not modal_is_open
    return modal_is_open

@callback(Output(ids.INPUTMOWOFFSETSTATE, 'value'),
          Output(ids.INPUTMOWOANGLESTATE, 'value'),
          Output(ids.INPUTMOWCUTEDGEBORDERSTATE, 'value'),
          Output(ids.INPUTDISTANCETOBORDERSTATE, 'value'),
          Output(ids.INPUTPATTERNSTATE, 'value'),
          Output(ids.INPUTMOWAREASTATE, 'value'),
          Output(ids.INPUTMOWCUTEDGEEXCLUSIONSTATE, 'value'),
          Output(ids.INPUTMOWCUTEDGEBORDERCCWSTATE, 'value'),
          [Input(ids.URLUPDATE, 'pathname')])
def update_pathplandersettings_on_reload(pathname: str) -> list:
    return pathplannercfgstate.width, pathplannercfgstate.angle, pathplannercfgstate.mowborder, pathplannercfgstate.distancetoborder, pathplannercfgstate.pattern, pathplannercfgstate.mowarea, pathplannercfgstate.mowexclusion, pathplannercfgstate.mowborderccw
    