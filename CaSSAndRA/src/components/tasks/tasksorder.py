from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

from src.components import ids
from . import buttons
from src.backend.data.mapdata import (current_map, 
                                      current_task, 
                                      tasks,
                                      )
from src.backend.data.scheduledata import schedule_tasks

tasksorder = dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Tasks'),
                        dbc.CardBody([
                            dcc.Dropdown(
                                id=ids.DROPDOWNTASKSORDER, 
                                className='m-1', 
                                multi=True, 
                                searchable=False
                            ),
                            dbc.Container([
                                    buttons.starttasksorder,
                                    buttons.loadtasksorder,
                                    buttons.renametask,
                                    buttons.removetask, 
                                    buttons.copytask,
                                    buttons.savenewtask, 
                            ], fluid=True),                       
                        ]), 
                    ], className='text-center m-1 w-90')
                ], style={"flex": "0 1 auto"})

@callback(Output(ids.DROPDOWNTASKSORDER, 'options'),
          Output(ids.MONDAYTASK, 'options'),
          Output(ids.TUESDAYTASK, 'options'),
          Output(ids.WEDNESDAYTASK, 'options'),
          Output(ids.THURSDAYTASK, 'options'),
          Output(ids.FRIDAYTASK, 'options'),
          Output(ids.SATURDAYTASK, 'options'),
          Output(ids.SUNDAYTASK, 'options'),
          [Input(ids.MODALRENAMETASK, 'is_open'),
           Input(ids.MODALSAVECURRENTTASK, 'is_open'),
           Input(ids.MODALREMOVETASK, 'is_open'),
           Input(ids.MODALCOPYTASK, 'is_open'),
           Input(ids.URLUPDATE, 'pathname'),
           State(ids.DROPDOWNTASKSORDER, 'options')])
def update_dropdown_tasksorder(rt_isopen: bool, 
                               st_isopnen: bool, 
                               dt_isopnen: bool, 
                               ct_isopen: bool, 
                               pathname: str, 
                               dropdown_opt_state: list()
                               ) -> list():
    time.sleep(0.5)
    context = ctx.triggered_id
    try:
        filtered_tasks = tasks.saved[tasks.saved['map name'] == current_map.name]
        options = filtered_tasks.name.unique() 
        options.sort()
    except:
        options = []
    return [options]*8   
