from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from src.backend.data.mapdata import current_map, current_task
from src.backend.map import path
from src.backend.comm import cmdlist
from src.backend.utils import debuglogger

#modalbuttons
okbuttonsavecurrenttask = dbc.Button('OK', id=ids.OKBUTTONSAVECURRENTTASK, class_name='ms-auto', n_clicks=0)
okbuttonremovetask = dbc.Button('OK', id=ids.OKBUTTONSREMOVETASK, class_name='ms-auto', n_clicks=0)

#selection buttons
starttask = dbc.Button(id=ids.BUTTONSTARTSELECTEDTASK, size='lg', class_name='mt-1 bi bi-cloud-download', n_clicks=0, title='start selected task')
plannewtask = dbc.Button(id=ids.BUTTONPLANNEWTASK, size='lg', class_name='mt-1 bi-file-earmark-plus', n_clicks=0, title='create new task')
savenewtask = dbc.Button(id=ids.BUTTONSAVECURRENTTASK, size='lg', class_name='mt-1 bi bi-cloud-plus', disabled=False, title='save task')
removetask = dbc.Button(id=ids.BUTTONREMOVETASK, size='lg', class_name='mt-1 bi bi-cloud-minus', n_clicks=0, title='remove selected task')

@callback(Output(ids.BUTTONSTARTSELECTEDTASK, 'active'),
          [Input(ids.BUTTONSTARTSELECTEDTASK, 'n_clicks')])
def start_selected_task(bsst_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONSTARTSELECTEDTASK:
        path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
        current_map.mowpath = current_map.preview
        current_map.mowpath['type'] = 'way'
        cmdlist.cmd_mow = True
    return False

@callback(Output(ids.BUTTONSTARTSELECTEDTASK, 'disabled'),
          Output(ids.BUTTONREMOVETASK, 'disabled'),
          [Input(ids.DROPDOWNCHOOSETASK, 'value')])
def update_saved_tasks_butttons_disabled(selected_task: str) -> list:
    if selected_task == '' or selected_task == None:
        return True, True
    else:
        return False, False
    
@callback(Output(ids.BUTTONSAVECURRENTTASK, 'disabled'),
          [Input(ids.TASKMAP, 'figure')])
def update_saved_tasks_button_save_disabled(fig: dict):
    if not current_task.preview.empty:
        return False
    else:
        return True
