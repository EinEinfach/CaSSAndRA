from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data.cfgdata import pathplannercfgstate

from . import mowsettingstemplate as mst

template = mst.get_mow_settings_template(ids.INPUTPATTERNSTATE, pathplannercfgstate.pattern,
                                        ids.INPUTMOWOFFSETSTATE, pathplannercfgstate.width,
                                        ids.INPUTMOWOANGLESTATE, pathplannercfgstate.angle,
                                        ids.INPUTDISTANCETOBORDERSTATE, pathplannercfgstate.distancetoborder,
                                        ids.INPUTMOWCUTEDGEBORDERSTATE, pathplannercfgstate.mowborder, 
                                        ids.INPUTMOWAREASTATE, pathplannercfgstate.mowarea,
                                        ids.INPUTMOWCUTEDGEEXCLUSIONSTATE, pathplannercfgstate.mowexclusion,
                                        ids.INPUTMOWCUTEDGEBORDERCCWSTATE, pathplannercfgstate.mowborderccw
                                        )

mowsettings = dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle('Mow settings')),
                dbc.ModalBody([
                    template,                    
                ], style={"padding-top" : 0, "padding-bottom" : 0}),
                dbc.ModalFooter(
                    dbc.Button('OK', id=ids.BUTTONOKINPUTMAPSETTINGS, className='ms-auto', n_clicks=0)
                ),
            ],id=ids.MODALMOWSETTINGS, is_open=False, centered=True, )

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
    if context == ids.BUTTONOKINPUTMAPSETTINGS:
        if pattern != 'lines' and pattern != 'squares' and pattern != 'rings':
            pathplannercfgstate.pattern = 'lines'
        else:
            pathplannercfgstate.pattern = pattern
        if mowoffset != None:
            pathplannercfgstate.width = mowoffset
        pathplannercfgstate.angle = mowangle
        if distancetoborder != None:
            pathplannercfgstate.distancetoborder = distancetoborder
        pathplannercfgstate.mowarea = mowarea
        pathplannercfgstate.mowexclusion = mowexclusion
        pathplannercfgstate.mowborderccw = mowborderccw
        pathplannercfgstate.mowborder = mowborder
            
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
    