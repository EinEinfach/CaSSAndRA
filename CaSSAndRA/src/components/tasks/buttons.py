from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from src.backend.data.mapdata import current_map, current_task
from src.backend.map import path
from src.backend.comm import cmdlist

#modalbuttons
okbuttonsavecurrenttask = dbc.Button('OK', id=ids.OKBUTTONSAVECURRENTTASK, class_name='ms-auto', n_clicks=0)
okbuttonremovetask = dbc.Button('OK', id=ids.OKBUTTONSREMOVETASK, class_name='ms-auto', n_clicks=0)

#selection buttons
starttask = dbc.Button(id=ids.BUTTONSTARTSELECTEDTASK, size='lg', class_name='me-1 mt-1 bi bi-play-fill', n_clicks=0, title='start selected task')
plannewtask = dbc.Button(id=ids.BUTTONPLANNEWTASK, size='lg', class_name='me-1 mt-1 bi-file-earmark-plus', n_clicks=0, title='create new task')
copyptask = dbc.Button(id=ids.BUTTONCOPYTASK, size='lg', class_name='mt-1 bi bi-clouds', n_clicks=0, title='copy selected task')
removetask = dbc.Button(id=ids.BUTTONREMOVETASK, size='lg', class_name='mt-1 bi bi-cloud-minus', n_clicks=0, title='remove selected task')

@callback(Output(ids.BUTTONSTARTSELECTEDTASK, 'active'),
          [Input(ids.BUTTONSTARTSELECTEDTASK, 'n_clicks')])
def start_selected_task(bsst_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONSTARTSELECTEDTASK:
        path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
        cmdlist.cmd_mow = True
    return False
