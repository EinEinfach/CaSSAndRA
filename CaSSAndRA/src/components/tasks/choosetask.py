from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from src.components import ids
from . import buttons
from src.backend.data.mapdata import current_map, current_task, tasks

choosetask = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Saved tasks'),
                        dbc.CardBody([
                            dcc.Dropdown(id=ids.DROPDOWNCHOOSETASK, className='m-1'),
                            dbc.Container([
                                    buttons.starttask,
                                    buttons.loadtask,
                                    buttons.plannewtask,
                                    buttons.savenewtask,
                                    buttons.removetask    
                            ], fluid=True),                     
                        ]), 
                    ], className='text-center m-1 w-90')
                ])

@callback(Output(ids.DROPDOWNCHOOSETASK, 'options'),
          Output(ids.DROPDOWNCHOOSETASK, 'value'),
          [Input(ids.OKBUTTONSAVECURRENTTASK, 'n_clicks'),
           Input(ids.BUTTONPLANNEWTASK, 'n_clicks'),
           Input(ids.MODALSAVECURRENTTASK, 'is_open'),
           Input(ids.MODALREMOVETASK, 'is_open'),
           State(ids.DROPDOWNCHOOSETASK, 'value'),
           State(ids.DROPDOWNCHOOSETASK, 'options')])
def update_dropdown_choosetask(bok_nclicks: int, bpnt_nclicks: int, save_is_open: bool, remove_is_open: bool,  
                                    dropdown_val_state: str(), dropdown_opt_state: list()) -> list():
    context = ctx.triggered_id
    try:
        filtered_tasks = tasks.saved[tasks.saved['map name'] == current_map.name]
        options = filtered_tasks.name.unique() 
        value = dropdown_val_state
    except:
        options = []
        value = None
    if context == ids.BUTTONPLANNEWTASK:
        value = None
        current_task.create()
    return options, value
