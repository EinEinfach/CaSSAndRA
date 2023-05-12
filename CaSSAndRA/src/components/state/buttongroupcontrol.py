from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from src.backend.comm import cmdlist
from src.backend.data import mapdata
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import current_map

buttonhome = dbc.Button(id=ids.BUTTONHOME, size='lg',class_name='mx-1 mt-1 bi bi-house', title='Go Home (dock)', disabled=False)
                
buttonmowall = dbc.Button(id=ids.BUTTONMOWALL, size='lg', class_name='me-1 mt-1 bi bi-map-fill', title='Mow All', disabled=False)

buttongoto = dbc.Button(id=ids.BUTTONGOTO, size='lg', class_name='me-1 mt-1 bi bi-geo-alt-fill', title='Select GoTo', disabled=False)

buttonzoneselect = dbc.Button(id=ids.BUTTONZONESELECT, size='lg', class_name='me-1 mt-1 bi bi-pin-map-fill', title='Select Zone to mow', disabled=False)

buttoncancel = dbc.Button(id=ids.BUTTONCANCEL, size='lg', class_name='me-1 mt-1 bi bi-x-square-fill', title='Cancel', disabled=False)

buttonmowsettings = dbc.Button(id=ids.BUTTONMOWSETTINGS, size='lg', class_name='me-1 mt-1 bi bi-gear-fill',title='Mower Settings', disabled=False)

buttongo = dbc.Button(id=ids.BUTTONGO, size='lg', class_name='mx-1 mt-1 bi bi-play-fill', title='Start Mowing', disabled=False)

buttonstop = dbc.Button(id=ids.BUTTONSTOP, size='lg', class_name='mx-1 mt-1 bi bi-stop-fill', color='danger', title='STOP', disabled=False)

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
            current_map.mowpath = current_map.preview
            current_map.mowpath['type'] = 'way'
            cmdlist.cmd_mow = True
        elif active_bzs:
            current_map.mowpath = current_map.preview
            current_map.mowpath['type'] = 'way'
            cmdlist.cmd_mow = True
        elif active_bgt:
            cmdlist.cmd_goto = True
        else:
            current_map.mowpath = robot.current_task
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

    if current_map.perimeter.empty:
        return True, True, True, True, True
    elif robot.job == 1 or robot.job == 4:
        return True, True, True, True, True
    else:
        return False, False, False, False, False 

