from dash import dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from . import buttons
from src.backend.data.mapdata import current_map, current_task, tasks

shortcuts = dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle('Shortcuts')),
                            dbc.ModalBody(
                                dcc.Dropdown(
                                    id=ids.DROPDOWNSHORTCUTS, 
                                    className='m-1', 
                                    multi=True, 
                                    searchable=False
                                ),
                            ),
                            dbc.ModalFooter([
                                buttons.okbuttonshortcuts,  
                            ] ),
                        ],
                        id=ids.MODALSHORTCUTS,
                        is_open=False, centered=True,
                    )

@callback(Output(ids.MODALSHORTCUTS, 'is_open'),
          [Input(ids.BUTTONSHORTCUTSELECT, 'n_clicks'),
           Input(ids.OKBUTTONSHORTCUTS, 'n_clicks'),
           ])
def select_shortcut(bss_nclicks: int,
                    bok_nclicks: int,
                    ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONSHORTCUTSELECT and bss_nclicks:
        return True
    else:
        return False

@callback(Output(ids.DROPDOWNSHORTCUTS, 'options'),
          [Input(ids.MODALSHORTCUTS, 'is_open'),
           State(ids.DROPDOWNSHORTCUTS, 'options'),
           ])
def update_dropdown_shortcuts(is_open: bool, 
                              dropdown_opt_state: list()   
                              ) -> list():
    context = ctx.triggered_id
    try:
        filtered_tasks = tasks.saved[tasks.saved['map name'] == current_map.name]
        options = filtered_tasks.name.unique() 
        options.sort()
    except:
        options = []
    if options == []:
        current_task.create()
    return options

