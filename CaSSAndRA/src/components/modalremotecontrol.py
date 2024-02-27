from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

from . import ids
from src.backend.comm import cmdlist
from src.backend.data.roverdata import robot
from src.backend import backendserver


confirm = dbc.Modal([
                        dbc.ModalHeader(dbc.ModalTitle(id=ids.MODALREMOTECONTROLHEADER)),
                        dbc.ModalBody(id=ids.MODALREMOTECONTROLCONTENT),
                        dbc.ModalFooter(
                            dbc.Button('OK', id=ids.BUTTONREMOTECONTROLOK, className='ms-auto', n_clicks=0)
                        ),
                ],id=ids.MODALREMOTECONTROL, is_open=False,
                )

@callback(Output(ids.MODALREMOTECONTROL, 'is_open'),
          (Output(ids.MODALREMOTECONTROLCONTENT, 'children')),
          (Output(ids.MODALREMOTECONTROLHEADER, 'children')),
          (Output(ids.BUTTONFAN, 'active')),
        [Input(ids.BUTTONSUNRAYOFF, 'n_clicks'), 
         Input(ids.BUTTONSUNRAYREBOOT, 'n_clicks')],
         Input(ids.BUTTONGPSREBOOT, 'n_clicks'),
         Input(ids.BUTTONFAN, 'n_clicks'),
         Input(ids.BUTTONREMOTECONTROLOK, 'n_clicks'),
        [State(ids.MODALREMOTECONTROL, 'is_open')],
)
def toggle_modal(n_clicks_bsoff: int, n_clicks_bsr: int, 
                 n_clicks_bgpsr: int, n_clicks_bfan: int,
                 n_clicks_bok: int, modal_is_open: bool) -> list:
    context = ctx.triggered_id

    if robot.last_mow_status:
        buttonfanactive = True
    else:
        buttonfanactive = False

    if context == ids.BUTTONSUNRAYOFF:
        cmdlist.cmd_standby = 'off'
        modalheader = 'Warning'
        modaltext = 'This will shutdown your rover. Do you want to continue?'
    elif context == ids.BUTTONSUNRAYREBOOT:
        cmdlist.cmd_standby = 'reboot'
        modalheader = 'Info'
        modaltext = 'Reboot Sunray FW and Backend-Server?'
    elif context == ids.BUTTONGPSREBOOT:
        cmdlist.cmd_standby = 'gps-reboot'
        modalheader = 'Info'
        modaltext = 'Reboot GPS Hardware?'
    elif context == ids.BUTTONFAN:
        if not buttonfanactive:
            cmdlist.cmd_standby = 'toggle-mow'
            modalheader = 'Warning'
            modaltext = 'Switch on Mow motor. Do you want to continue?'
        else:
            cmdlist.cmd_standby = 'toggle-mow'
            modalheader = 'Info'
            modaltext = 'Switch off Mow motor?'
    else:
        modalheader = ''
        modaltext = ''

    if context == ids.BUTTONREMOTECONTROLOK:
        if cmdlist.cmd_standby == 'off':
            cmdlist.cmd_shutdown = True
            cmdlist.cmd_standby = ''
            time.sleep(5)
            backendserver.shutdown()
        elif cmdlist.cmd_standby == 'reboot':
            cmdlist.cmd_reboot = True
            cmdlist.cmd_standby = ''
            time.sleep(5)
            backendserver.reboot()
        elif cmdlist.cmd_standby == 'gps-reboot':
            cmdlist.cmd_gps_reboot = True
            cmdlist.cmd_standby = ''
        elif cmdlist.cmd_standby == 'toggle-mow':
            cmdlist.cmd_toggle_mow_motor = True
            cmdlist.cmd_standby = ''
        else:
            cmdlist.cmd_standby = ''

    if n_clicks_bsoff or n_clicks_bsr or n_clicks_bgpsr or n_clicks_bfan:
        return not modal_is_open, modaltext, modalheader, buttonfanactive
    return modal_is_open, modaltext, modalheader, buttonfanactive