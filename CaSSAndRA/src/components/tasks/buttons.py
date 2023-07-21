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

#selection buttons (saved tasks)
starttask = dbc.Button(id=ids.BUTTONSTARTSELECTEDTASK, size='lg', class_name='mt-1 me-1 bi bi-play-fill', n_clicks=0, title='start selected task')
loadtask = dbc.Button(id=ids.BUTTONLOADSELECTEDTASK, size='lg', class_name='mt-1 me-1 bi bi-cloud-download', n_clicks=0, title='load selected task')
plannewtask = dbc.Button(id=ids.BUTTONPLANNEWTASK, size='lg', class_name='mt-1 me-1 bi-file-earmark-plus', n_clicks=0, title='create new task')
savenewtask = dbc.Button(id=ids.BUTTONSAVECURRENTTASK, size='lg', class_name='mt-1 me-1 bi bi-cloud-plus', disabled=False, title='save task')
removetask = dbc.Button(id=ids.BUTTONREMOVETASK, size='lg', class_name='mt-1 me-1 bi bi-cloud-minus', n_clicks=0, title='remove selected task')

#selection buttons (tasks order)
starttasksorder = dbc.Button(id=ids.BUTTONSTARTSELECTEDTASKSORDER, size='lg', class_name='mt-1 me-1 bi bi-play-fill', n_clicks=0, title='start selected tasks order')
loadtasksorder = dbc.Button(id=ids.BUTTONLOADSELECTEDTASKSORDER, size='lg', class_name='mt-1 me-1 bi bi-cloud-download', n_clicks=0, title='load selected tasks order')
savetasksorder = dbc.Button(id=ids.BUTTONSAVETASKSORDER, size='lg', class_name='mt-1 me-1 bi bi-cloud-plus', disabled=False, title='save tasks order as new task')

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

@callback(Output(ids.BUTTONLOADSELECTEDTASK, 'active'),
          [Input(ids.BUTTONLOADSELECTEDTASK, 'n_clicks')])
def load_selected_task(blst_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONLOADSELECTEDTASK:
        path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
    return False

@callback(Output(ids.BUTTONSTARTSELECTEDTASK, 'disabled'),
          Output(ids.BUTTONLOADSELECTEDTASK, 'disabled'),
          Output(ids.BUTTONREMOVETASK, 'disabled'),
          [Input(ids.DROPDOWNCHOOSETASK, 'value')])
def update_saved_tasks_butttons_disabled(selected_task: str) -> list:
    if selected_task == '' or selected_task == None:
        return True, True, True
    else:
        return False, False, False
    
@callback(Output(ids.BUTTONSAVECURRENTTASK, 'disabled'),
          [Input(ids.TASKMAP, 'figure')])
def update_saved_tasks_button_save_disabled(fig: dict):
    if not current_task.preview.empty:
        return False
    else:
        return True

@callback(Output(ids.BUTTONSTARTSELECTEDTASKSORDER, 'active'),
          [Input(ids.BUTTONSTARTSELECTEDTASKSORDER, 'n_clicks')])
def start_selected_tasks_order(bsst_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONSTARTSELECTEDTASKSORDER:
        path.calc_task(current_task.tasks_order, current_task.tasks_order_parameters)
        current_map.mowpath = current_map.preview
        current_map.mowpath['type'] = 'way'
        cmdlist.cmd_mow = True
    return False

@callback(Output(ids.BUTTONLOADSELECTEDTASKSORDER, 'active'),
          [Input(ids.BUTTONLOADSELECTEDTASKSORDER, 'n_clicks')])
def load_selected_tasks_order(blsto_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONLOADSELECTEDTASKSORDER:
        path.calc_task(current_task.tasks_order, current_task.tasks_order_parameters)
    return False

@callback(Output(ids.BUTTONSTARTSELECTEDTASKSORDER, 'disabled'),
          Output(ids.BUTTONLOADSELECTEDTASKSORDER, 'disabled'),
          Output(ids.BUTTONSAVETASKSORDER, 'disabled'),
          [Input(ids.DROPDOWNTASKSORDER, 'value')])
def update_tasks_order_butttons_disabled(tasks_order: str) -> list:
    if tasks_order == '' or tasks_order == None:
        return True, True, True
    else:
        return False, False, False