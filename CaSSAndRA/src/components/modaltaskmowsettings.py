from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data.cfgdata import pathplannercfgtask

from . import mowsettingstemplate as mst

template = mst.get_mow_settings_template(ids.INPUTPATTERNTASK, pathplannercfgtask.pattern,
                                        ids.INPUTMOWOFFSETTASK, pathplannercfgtask.width,
                                        ids.INPUTMOWOANGLETASK, pathplannercfgtask.angle,
                                        ids.INPUTDISTANCETOBORDERTASK, pathplannercfgtask.distancetoborder,
                                        ids.INPUTMOWCUTEDGEBORDERTASK, pathplannercfgtask.mowborder, 
                                        ids.INPUTMOWAREATASK, pathplannercfgtask.mowarea,
                                        ids.INPUTMOWCUTEDGEEXCLUSIONTASK, pathplannercfgtask.mowexclusion,
                                        ids.INPUTMOWCUTEDGEBORDERCCWTASK, pathplannercfgtask.mowborderccw
                                        )

mowsettings = dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle('Mow settings')),
                dbc.ModalBody([
                    template,               
                ], style={"padding-top" : 0, "padding-bottom" : 0}),
                dbc.ModalFooter(
                    dbc.Button('OK', id=ids.BUTTONOKINPUTMOWTASKSETTINGS, className='ms-auto', n_clicks=0)
                ),
            ],id=ids.MODALMOWTASKSETTINGS, is_open=False, centered=True)

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
def toggle_modal(n_clicks_bms: int, 
                 n_clicks_bok: int,
                 modal_is_open: bool, 
                 pattern: str,
                 mowoffset: float, 
                 mowangle: int,
                 distancetoborder: int, 
                 mowarea: bool,
                 mowborder: str, 
                 mowexclusion: bool,
                 mowborderccw: bool
                 ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKINPUTMOWTASKSETTINGS:
        if pattern != 'lines' and pattern != 'squares' and pattern != 'rings':
            pathplannercfgtask.pattern = 'lines'
        else:
            pathplannercfgtask.pattern = pattern
        if mowoffset != None:
            pathplannercfgtask.width = mowoffset
        pathplannercfgtask.angle = mowangle
        if distancetoborder != None:
            pathplannercfgtask.distancetoborder = distancetoborder
        pathplannercfgtask.mowarea = mowarea
        pathplannercfgtask.mowexclusion = mowexclusion
        pathplannercfgtask.mowborderccw = mowborderccw
        pathplannercfgtask.mowborder = mowborder
            
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
    
