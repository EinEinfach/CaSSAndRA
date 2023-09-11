from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from . import buttons
from src.backend.data import saveddata
from src.backend.data.mapdata import current_map, current_task, tasks
from src.backend.data.roverdata import robot

savecurrenttask = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle('Info')),
                            dbc.ModalBody('Please give a unique name for planned task'),
                            dbc.ModalBody(dbc.Input(id=ids.INPUTTASKNAME, type='text')),
                            dbc.ModalFooter([
                                buttons.okbuttonsavecurrenttask,  
                            ] ),
                        ],
                        id=ids.MODALSAVECURRENTTASK,
                        is_open=False,
                    )

removecurrenttask = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle('Warning')),
                            dbc.ModalBody('Remove selected task?'),
                            dbc.ModalFooter([
                                buttons.okbuttonremovetask,  
                                ] 
                            ),
                        ],
                        id=ids.MODALREMOVETASK,
                        is_open=False,          
                    )

renametask = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle('Info')),
                            dbc.ModalBody('Rename selected task?'),
                            dbc.ModalBody(dbc.Input(id=ids.INPUTNEWTASKNAME, type='text')),
                            dbc.ModalFooter([
                                buttons.okbuttonrenametask,  
                                ] 
                            ),
                        ],
                        id=ids.MODALRENAMETASK,
                        is_open=False,          
                    )

copytask = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle('Info')),
                            dbc.ModalBody('Copy selected task?'),
                            dbc.ModalBody(dbc.Input(id=ids.INPUTCOPIEDTASKNAME, type='text')),
                            dbc.ModalFooter([
                                buttons.okbuttoncopytask,  
                                ] 
                            ),
                        ],
                        id=ids.MODALCOPYTASK,
                        is_open=False,          
                    )

@callback(Output(ids.MODALSAVECURRENTTASK, 'is_open'),
          [Input(ids.BUTTONSAVECURRENTTASK, 'n_clicks'),
           Input(ids.OKBUTTONSAVECURRENTTASK, 'n_clicks'),
           State(ids.MODALSAVECURRENTTASK, 'is_open'),
           State(ids.INPUTTASKNAME, 'value')])
def save_current_task(bsct_nclicks: int, 
                      bok_nclicks,  
                      is_open: bool, 
                      task_name: str(),
                      ) -> bool:
    context = ctx.triggered_id
    if context == ids.OKBUTTONSAVECURRENTTASK:
        if not current_task.preview.empty:
            current_task.create_subtask()
        saveddata.save_task(tasks.saved, tasks.saved_parameters, current_task.subtasks, current_task.subtasks_parameters, task_name)
        return False
    if context == ids.BUTTONSAVECURRENTTASK and bsct_nclicks:
        return True
    return False

@callback(Output(ids.MODALREMOVETASK, 'is_open'),
          [Input(ids.BUTTONREMOVETASK, 'n_clicks'),
           Input(ids.OKBUTTONSREMOVETASK, 'n_clicks'),
           State(ids.MODALREMOVETASK, 'is_open'),
           State(ids.DROPDOWNTASKSORDER, 'value')])
def remove_selected_task(brt_nclicks: int, 
                         bok_nclicks,  
                         is_open: bool, 
                         task_name: list(),
                         ) -> bool:
    context = ctx.triggered_id
    if context == ids.OKBUTTONSREMOVETASK and task_name is not None:
        saveddata.remove_task(tasks.saved, tasks.saved_parameters, task_name, current_map.name)
        return False
    if context == ids.BUTTONREMOVETASK and brt_nclicks:
        return True
    return False

@callback(Output(ids.MODALRENAMETASK, 'is_open'),
          [Input(ids.BUTTONRENAMETASK, 'n_clicks'),
           Input(ids.OKBUTTONSRRENAMETASK, 'n_clicks'),
           State(ids.MODALRENAMETASK, 'is_open'),
           State(ids.INPUTNEWTASKNAME, 'value'), 
           State(ids.DROPDOWNTASKSORDER, 'value')])
def rename_selected_task(brt_nclicks: int, 
                         bok_nclicks,  
                         is_open: bool, 
                         task_name: list(), 
                         task_old_name: list()
                         ) -> bool:
    context = ctx.triggered_id
    if context == ids.OKBUTTONSRRENAMETASK and task_name is not None:
        saveddata.save_task(tasks.saved, tasks.saved_parameters, current_task.subtasks, current_task.subtasks_parameters, task_name)
        saveddata.remove_task(tasks.saved, tasks.saved_parameters, task_old_name, current_map.name)
        return False
    if context == ids.BUTTONRENAMETASK and brt_nclicks:
        return True
    return False

@callback(Output(ids.MODALCOPYTASK, 'is_open'),
          [Input(ids.BUTTONCOPYTASK, 'n_clicks'),
           Input(ids.OKBUTTONCOPYTASK, 'n_clicks'),
           State(ids.MODALCOPYTASK, 'is_open'),
           State(ids.INPUTCOPIEDTASKNAME, 'value')])
def copy_selected_task(bct_nclicks: int, 
                       bok_nclicks,  
                       is_open: bool, 
                       task_name: list()
                       ) -> bool:
    context = ctx.triggered_id
    if context == ids.OKBUTTONCOPYTASK and task_name is not None:
        saveddata.save_task(tasks.saved, tasks.saved_parameters, current_task.subtasks, current_task.subtasks_parameters, task_name)
        return False
    if context == ids.BUTTONCOPYTASK and bct_nclicks:
        return True
    return False