from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from src.components import ids
from . import buttons
from src.backend.data.mapdata import current_map, current_task, tasks

tasksorder = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Tasks order'),
                        dbc.CardBody([
                            dcc.Dropdown(id=ids.DROPDOWNTASKSORDER, className='m-1', multi=True),
                            dbc.Container([
                                    buttons.starttasksorder,
                                    buttons.loadtasksorder,
                                    buttons.savetasksorder,  
                            ], fluid=True),                       
                        ]), 
                    ], className='text-center m-1 w-90')
                ])

@callback(Output(ids.DROPDOWNTASKSORDER, 'options'),
          [Input(ids.DROPDOWNCHOOSETASK, 'options'),
           State(ids.DROPDOWNCHOOSETASK, 'options')])
def update_dropdown_tasksorder(dropdown_opt: list, dropdown_opt_state: list()) -> list():
    context = ctx.triggered_id
    try:
        filtered_tasks = tasks.saved[tasks.saved['map name'] == current_map.name]
        options = filtered_tasks.name.unique() 
    except:
        options = []
    return options
