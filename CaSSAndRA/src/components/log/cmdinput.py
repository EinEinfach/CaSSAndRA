from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

#local imports
from .. import ids
from src.backend.comm import cmdlist

cmdinput = dbc.Input(id=ids.INPUTCUSTOMCMD, placeholder='every AT+ command supported by your comm.cpp', value='AT+', class_name='mt-2')
cmdsend = dbc.Button(id=ids.BUTTONSENDCUSTOMCMD, size='lg', class_name='me-1 mt-1 mb-1 bi bi-send-fill', disabled=False, title='send command to rover')

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
    