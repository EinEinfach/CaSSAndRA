from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from src.backend.data.mapdata import current_map, current_task, tasks
from src.backend.data import saveddata
from src.backend.map import path
from src.backend.comm import cmdlist

#modalbuttons
okbuttonsavecurrenttask = dbc.Button('OK', id=ids.OKBUTTONSAVECURRENTTASK, class_name='ms-auto', n_clicks=0)
okbuttonremovetask = dbc.Button('OK', id=ids.OKBUTTONSREMOVETASK, class_name='ms-auto', n_clicks=0)
okbuttonrenametask = dbc.Button('OK', id=ids.OKBUTTONSRRENAMETASK, class_name='ms-auto', n_clicks=0)
okbuttoncopytask = dbc.Button('OK', id=ids.OKBUTTONCOPYTASK, class_name='ms-auto', n_clicks=0)

#selection buttons (saved tasks)
starttasksorder = dbc.Button(id=ids.BUTTONSTARTSELECTEDTASKSORDER, class_name='mt-1 me-1 bi bi-play-fill btn-success', n_clicks=0, title='start selected tasks order')
loadtasksorder = dbc.Button(id=ids.BUTTONLOADSELECTEDTASKSORDER, class_name='mt-1 me-1 bi bi-cloud-download btn-info', n_clicks=0, title='load selected tasks order')
savenewtask = dbc.Button(id=ids.BUTTONSAVECURRENTTASK, class_name='mt-1 me-1 bi bi-floppy btn-success', disabled=False, title='save task')
removetask = dbc.Button(id=ids.BUTTONREMOVETASK, class_name='mt-1 me-1 bi bi-trash', n_clicks=0, title='remove selected task')
renametask = dbc.Button(id=ids.BUTTONRENAMETASK, class_name='mt-1 me-1 bi bi-pencil-square', n_clicks=0, title='rename selected task')
copytask = dbc.Button(id=ids.BUTTONCOPYTASK, class_name='mt-1 me-1 bi bi-copy', n_clicks=0, title='copy selected task')
    
@callback(Output(ids.BUTTONSAVECURRENTTASK, 'disabled'),
          [Input(ids.TASKMAP, 'figure'),
           State(ids.DROPDOWNTASKSORDER, 'value')])
def update_saved_tasks_button_save_disabled(fig: dict, tasks_order: list()):
    if not current_task.preview.empty:
        return False
    elif tasks_order != None and len(tasks_order) > 1:
        return False
    else:
        return True

@callback(Output(ids.BUTTONSTARTSELECTEDTASKSORDER, 'active'),
          [Input(ids.BUTTONSTARTSELECTEDTASKSORDER, 'n_clicks')])
def start_selected_tasks_order(bsst_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONSTARTSELECTEDTASKSORDER:
        current_map.task_progress = 0
        current_map.calculating = True
        path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
        if len(current_task.subtasks['name'].unique()) == 1:
            saveddata.update_task_preview(tasks.saved, current_map.preview)
        current_map.calculating = False
        current_map.mowpath = current_map.preview
        current_map.mowpath['type'] = 'way'
        cmdlist.cmd_mow = True
    return False

@callback(Output(ids.BUTTONLOADSELECTEDTASKSORDER, 'active'),
          [Input(ids.BUTTONLOADSELECTEDTASKSORDER, 'n_clicks')])
def load_selected_tasks_order(blsto_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONLOADSELECTEDTASKSORDER:
        current_map.task_progress = 0
        current_map.calculating = True
        path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
        if len(current_task.subtasks['name'].unique()) == 1:
            saveddata.update_task_preview(tasks.saved, current_map.preview)
        current_map.calculating = False
        current_map.mowpath = current_map.preview
        current_map.mowpath['type'] = 'way'
        cmdlist.cmd_take_map = True
    return False

@callback(Output(ids.BUTTONSTARTSELECTEDTASKSORDER, 'disabled'),
          Output(ids.BUTTONLOADSELECTEDTASKSORDER, 'disabled'),
          Output(ids.BUTTONREMOVETASK, 'disabled'),
          Output(ids.BUTTONRENAMETASK, 'disabled'),
          Output(ids.BUTTONCOPYTASK, 'disabled'),
          [Input(ids.DROPDOWNTASKSORDER, 'value')])
def update_tasks_order_butttons_disabled(tasks_order: list()) -> list:
    if tasks_order == [] or tasks_order == None:
        return True, True, True, True, True
    if len(tasks_order) == 1:
        return False, False, False, False, False
    else:
        return False, False, True, True, True

@callback(Output(ids.DROPDOWNTASKSORDER, 'value'),
          [Input(ids.BUTTONPLANCANCEL, 'n_clicks'),
           Input(ids.OKBUTTONSREMOVETASK, 'n_clicks'),
           State(ids.DROPDOWNTASKSORDER, 'value')])
def reset_tasks_order_selection(bc_nclicks: int, bok_nclicks: int, tasks_order: list()) -> list:
    context = ctx.triggered_id 
    if (context == ids.BUTTONPLANCANCEL and current_task.preview.empty) or context == ids.OKBUTTONSREMOVETASK:
        return []
    else:
        return tasks_order
