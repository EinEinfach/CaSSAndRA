from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

#local imports
from .. import ids
from src.backend.comm import cmdlist

cmdinput = dbc.Input(id=ids.INPUTCUSTOMCMD, placeholder='every AT+ command supported by your comm.cpp', value='AT+', class_name='mt-2')
cmdsend = dbc.Button(id=ids.BUTTONSENDCUSTOMCMD, size='lg', class_name='me-1 mt-1 mb-1 bi bi-send-fill', disabled=False, title='send command to rover')
logpaused = dbc.Button(id=ids.BUTTONLOGPAUSED, size='lg', class_name='me-1 mt-1 mb-1 bi bi-pause-fill', disabled=False, title='pause log update')

@callback(Output(ids.BUTTONSENDCUSTOMCMD, 'active'),
          Output(ids.INPUTCUSTOMCMD, 'value'),
          [Input(ids.BUTTONSENDCUSTOMCMD, 'n_clicks'),
           State(ids.INPUTCUSTOMCMD, 'value')])
def send_custom_cmd(bscc_nclicks: int,
                    customcmd: str,
                    ) -> list:
    context = ctx.triggered_id
    if context == ids.BUTTONSENDCUSTOMCMD and bscc_nclicks:
        cmdlist.cmd_custom_str = customcmd
        cmdlist.cmd_custom = True
        time.sleep(0.5)
    return False, ''

@callback(Output(ids.BUTTONLOGPAUSED, 'active'),
          [Input(ids.BUTTONLOGPAUSED, 'n_clicks'),
           State(ids.BUTTONLOGPAUSED, 'active')
           ])
def update_paused_button_active(blp_nclicks: int,
                                blp_state: bool,
                                ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONLOGPAUSED and blp_nclicks:
        return not blp_state
    else:
        return blp_state