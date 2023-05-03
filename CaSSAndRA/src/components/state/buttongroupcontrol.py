from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
from datetime import datetime

from .. import ids
from src.backend.comm import cmdlist
from src.backend.map import path
from src.backend.data import mapdata, roverdata, appdata
from src.backend.data.roverdata import robot

buttonhome = dbc.Button(id=ids.BUTTONHOME, size='lg',class_name='mx-1 mt-1 bi bi-house', disabled=False)
                
buttonmowall = dbc.Button(id=ids.BUTTONMOWALL, size='lg', class_name='me-1 mt-1 bi bi-map-fill', disabled=False)

buttongoto = dbc.Button(id=ids.BUTTONGOTO, size='lg', class_name='me-1 mt-1 bi bi-geo-alt-fill', disabled=False)

buttonzoneselect = dbc.Button(id=ids.BUTTONZONESELECT, size='lg', class_name='me-1 mt-1 bi bi-pin-map-fill', disabled=False)

buttoncancel = dbc.Button(id=ids.BUTTONCANCEL, size='lg', class_name='me-1 mt-1 bi bi-x-square-fill', disabled=False)

buttonmowsettings = dbc.Button(id=ids.BUTTONMOWSETTINGS, size='lg', class_name='me-1 mt-1 bi bi-gear-fill', disabled=False)

buttongo = dbc.Button(id=ids.BUTTONGO, size='lg', class_name='mx-1 mt-1 bi bi-play-fill', disabled=False)

buttonstop = dbc.Button(id=ids.BUTTONSTOP, size='lg', class_name='mx-1 mt-1 bi bi-stop-fill', color='danger', disabled=False)

#Create state of buttons
@callback(Output(ids.BUTTONHOME, 'active'),
          Output(ids.BUTTONMOWALL, 'active'),
           Output(ids.BUTTONZONESELECT, 'active'),
           Output(ids.BUTTONGOTO, 'active'),
          [Input(ids.BUTTONHOME, 'n_clicks'),
           Input(ids.BUTTONMOWALL, 'n_clicks'),
           Input(ids.BUTTONZONESELECT, 'n_clicks'),
           Input(ids.BUTTONGOTO, 'n_clicks'),
           Input(ids.BUTTONCANCEL, 'n_clicks'),
           Input(ids.BUTTONGO, 'n_clicks'),
           Input(ids.BUTTONSTOP, 'n_clicks')])
def update_button_active(n_clicks_bh: int, n_clicks_bma: int,
                              n_clicks_bzs: int, n_clicks_bgt: int,
                              n_clicks_bc: int, n_clicks_bgo: int,
                              n_clicks_bs: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONHOME:
        if n_clicks_bh > 0 :
            return True, False, False, False
        else:
            return False, False, False, False
    elif context == ids.BUTTONMOWALL:
        if n_clicks_bma > 0:
            return False, True, False, False
        else:
            return False, False, False, False
    elif context == ids.BUTTONZONESELECT:
        if n_clicks_bzs > 0:
            return False, False, True, False
        else:
            return False, False, False, False
    elif context == ids.BUTTONGOTO:
        if n_clicks_bgt > 0:
            return False, False, False, True
        else:
            return False, False, False, False
    else:
        return False, False, False, False

#Perform command
@callback(Output(ids.BUTTONGO, 'active'),
          Output(ids.BUTTONSTOP, 'active'),
          [Input(ids.BUTTONGO, 'n_clicks'),
           Input(ids.BUTTONSTOP, 'n_clicks'),
           Input(ids.BUTTONGO, 'active'),
           Input(ids.BUTTONSTOP, 'active'),
           Input(ids.INTERVAL, 'n_intervals'),
           State(ids.BUTTONHOME, 'active'),
           State(ids.BUTTONMOWALL, 'active'),
           State(ids.BUTTONZONESELECT, 'active'),
           State(ids.BUTTONGOTO, 'active')])
def perfom_cmd(n_clicks_bgo: int, n_clicks_bs: int,
               buttongostate: bool, buttonstopstate: bool, n_intervals: int,
               active_bh: bool, active_bma: bool, 
               active_bzs: bool, active_bgt: bool) -> list():
    
    context = ctx.triggered_id
    rover_state = robot.status

    if context == ids.BUTTONGO:
        buttongostate = True
        buttonstopstate = False
        if active_bh:
            cmdlist.cmd_dock = True
        elif active_bma:
            mapdata.mowpath = mapdata.preview
            mapdata.mowpath['type'] = 'way'
            cmdlist.cmd_mow = True
        elif active_bzs:
            mapdata.mowpath = mapdata.preview
            mapdata.mowpath['type'] = 'way'
            cmdlist.cmd_mow = True
        elif active_bgt:
            cmdlist.cmd_goto = True
        else:
            mapdata.mowpath = roverdata.current_task
            cmdlist.cmd_resume = True
    
    if context == ids.BUTTONSTOP:
        buttongostate = False
        buttonstopstate = True
        cmdlist.cmd_stop = True
    
    if context == ids.INTERVAL:
        if rover_state == 'mow' or rover_state == 'docking':
            buttongostate = True
            buttonstopstate = False
        else:
            buttongostate = False
            buttonstopstate = False
    

    return buttongostate, buttonstopstate

#Disable select buttons during task
@callback(Output(ids.BUTTONHOME, 'disabled'),
          Output(ids.BUTTONMOWALL, 'disabled'),
          Output(ids.BUTTONZONESELECT, 'disabled'),
          Output(ids.BUTTONGOTO, 'disabled'),
          Output(ids.BUTTONCANCEL, 'disabled'),
          [Input(ids.INTERVAL, 'n_intervals'),
           Input(ids.BUTTONGO, 'n_clicks'),
           Input(ids.BUTTONSTOP, 'n_clicks'),
           State(ids.BUTTONHOME, 'disabled'),
           State(ids.BUTTONMOWALL, 'disabled'),
           State(ids.BUTTONZONESELECT, 'disabled'),
           State(ids.BUTTONGOTO, 'disabled'),
           State(ids.BUTTONCANCEL, 'disabled')])
def update_button_disabled(n_intervals: int, n_clicks_bgo: int, n_clicks_bs: int,
                           bh_disabled: bool, bma_disabled: bool, bzs_disabled: bool,
                           bgt_disabled: bool, bc_disabled: bool) -> list():
    context = ctx.triggered_id

    if mapdata.perimeter.empty:
        return True, True, True, True, True

    # if context == ids.INTERVAL and time_since_buttongo.seconds > 15:
    #     if current_rover_state != 'mow' and current_rover_state != 'docking' and current_rover_state != 'error':
    #         return False, False, False, False, False
    #     else:
    #         return True, True, True, True, True
    elif context == ids.BUTTONGO:
        appdata.time_buttongo_pressed = datetime.now()
        return True, True, True, True, True
    elif context == ids.BUTTONSTOP:
        return False, False, False, False, False
    else:
        return bh_disabled, bma_disabled, bzs_disabled, bgt_disabled, bc_disabled


