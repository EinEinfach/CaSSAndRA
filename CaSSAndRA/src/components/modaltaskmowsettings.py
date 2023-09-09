from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data.cfgdata import pathplannercfgtask

mowsettings = dbc.Modal([
                        dbc.ModalHeader(dbc.ModalTitle('Mow settings')),
                        dbc.ModalBody([
                            html.P(['pattern'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTPATTERNTASK, 
                                options=[
                                    {'label': 'lines', 'value': 'lines'},
                                    {'label': 'squares', 'value': 'squares'},
                                    {'label': 'rings', 'value': 'rings'},
                                ],
                                value=pathplannercfgtask.pattern
                            ),
                            html.P(['width'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWOFFSETTASK, 
                                      value=pathplannercfgtask.width, 
                                      type='number', 
                                      min=0, 
                                      max=1, 
                                      step=0.01, 
                                      size='sm'
                            ), 
                            html.P(['angle'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWOANGLETASK, 
                                      value=pathplannercfgtask.angle, 
                                      type='number', 
                                      min=0, 
                                      max=359, 
                                      step=1, 
                                      size='sm'
                            ),
                            html.P(['distance to border'], className='mb-0'),
                            dbc.Input(id=ids.INPUTDISTANCETOBORDERTASK, 
                                      value=pathplannercfgtask.distancetoborder, 
                                      type='number', 
                                      min=0, 
                                      max=5, 
                                      step=1, 
                                      size='sm'
                            ),
                            html.P(['mow area'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTMOWAREATASK, 
                                options=[
                                    {'label': 'yes', 'value': 'yes'},
                                    {'label': 'no', 'value': 'no'}
                                ],
                                value=pathplannercfgtask.mowarea
                            ),
                            html.P(['mow cut edge border (laps)'], className='mb-0'),
                            dbc.Input(id=ids.INPUTMOWCUTEDGEBORDERTASK, 
                                      value=pathplannercfgtask.mowborder, 
                                      type='number', 
                                      min=0, 
                                      max=6, 
                                      step=1, 
                                      size='sm'
                            ),
                            html.P(['mow cut edge exclusion'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTMOWCUTEDGEEXCLUSIONTASK, 
                                options=[
                                    {'label': 'yes', 'value': 'yes'},
                                    {'label': 'no', 'value': 'no'}
                                ],
                                value=pathplannercfgtask.mowexclusion
                            ),
                            html.P(['mow cut edge border in ccw'], className='mb-0'),
                            dbc.Select(
                                id=ids.INPUTMOWCUTEDGEBORDERCCWTASK, 
                                options=[
                                    {'label': 'yes', 'value': 'yes'},
                                    {'label': 'no', 'value': 'no'}
                                ],
                                value=pathplannercfgtask.mowborderccw
                            ),
                        ]),
                        dbc.ModalFooter(
                            dbc.Button('OK', id=ids.BUTTONOKINPUTMOWTASKSETTINGS, className='ms-auto', n_clicks=0)
                        ),
                ],id=ids.MODALMOWTASKSETTINGS, is_open=False,
                )

@callback(Output(ids.MODALMOWTASKSETTINGS, 'is_open'),
          [Input(ids.BUTTONPLANMOWSETTINGS, 'n_clicks'),
           Input(ids.BUTTONOKINPUTMOWTASKSETTINGS, 'n_clicks'),
           State(ids.MODALMOWTASKSETTINGS, 'is_open'),
           State(ids.INPUTPATTERNTASK, 'value'),
           State(ids.INPUTMOWOFFSETTASK, 'value'),
           State(ids.INPUTMOWOANGLETASK, 'value'),
           State(ids.INPUTDISTANCETOBORDERTASK, 'value'),
           State(ids.INPUTMOWAREATASK, 'value'),
           State(ids.INPUTMOWCUTEDGEBORDERTASK, 'value'),
           State(ids.INPUTMOWCUTEDGEEXCLUSIONTASK, 'value'),
           State(ids.INPUTMOWCUTEDGEBORDERCCWTASK, 'value')])
def toggle_modal(n_clicks_bms: int, n_clicks_bok: int,
                 modal_is_open: bool, pattern: str(),
                 mowoffset: float, mowangle: int,
                 distancetoborder: int, mowarea: str,
                 mowborder: str, mowexclusion: str,
                 mowborderccw: str) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKINPUTMOWTASKSETTINGS:
        if pattern != 'lines' and pattern != 'squares' and pattern != 'rings':
            pathplannercfgtask.pattern = 'lines'
        else:
            pathplannercfgtask.pattern = pattern
        if mowoffset != None:
            pathplannercfgtask.width = mowoffset
        if mowangle != None:
            pathplannercfgtask.angle = mowangle
        if distancetoborder != None:
            pathplannercfgtask.distancetoborder = distancetoborder
        pathplannercfgtask.mowarea = mowarea
        pathplannercfgtask.mowborder = mowborder
        pathplannercfgtask.mowexclusion = mowexclusion
        pathplannercfgtask.mowborderccw = mowborderccw
            
    if n_clicks_bms or n_clicks_bok:
        return not modal_is_open
    return modal_is_open

@callback(Output(ids.INPUTMOWOFFSETTASK, 'value'),
          Output(ids.INPUTMOWOANGLETASK, 'value'),
          Output(ids.INPUTMOWCUTEDGEBORDERTASK, 'value'),
          Output(ids.INPUTDISTANCETOBORDERTASK, 'value'),
          Output(ids.INPUTPATTERNTASK, 'value'),
          Output(ids.INPUTMOWAREATASK, 'value'),
          Output(ids.INPUTMOWCUTEDGEEXCLUSIONTASK, 'value'),
          Output(ids.INPUTMOWCUTEDGEBORDERCCWTASK, 'value'),
          [Input(ids.URLUPDATE, 'pathname')])
def update_pathplandersettings_on_reload(pathname: str) -> list:
    return pathplannercfgtask.width, pathplannercfgtask.angle, pathplannercfgtask.mowborder, pathplannercfgtask.distancetoborder, pathplannercfgtask.pattern, pathplannercfgtask.mowarea, pathplannercfgtask.mowexclusion, pathplannercfgtask.mowborderccw
    