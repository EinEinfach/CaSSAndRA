from dash import html, Input, Output, State, callback, ctx, Patch
import plotly.graph_objects as go
import pandas as pd

from .. import ids
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import current_map, current_task, tasks, progress_color_palette, tasks_color_palette
from src.backend.data.cfgdata import pathplannercfgtask
from src.backend.map import map, path

tasksmap = go.Figure()
tasksmap.update_layout(
               plot_bgcolor='white',
               yaxis=dict(
                    scaleratio=1, 
                    scaleanchor='x',
                    gridcolor = '#eeeeee', 
                    zerolinecolor = 'lightgrey',
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False,
                    ),
               xaxis=dict(
                    gridcolor = '#eeeeee', 
                    zerolinecolor = 'lightgrey',
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False,
               ),
               margin=dict(
                    b=0, #bottom margin 40px
                    l=0, #left margin 40px
                    r=0, #right margin 20px
                    t=0, #top margin 20px
                ),
               showlegend=False,
               uirevision=True,
               hovermode='closest',
               dragmode='pan',
               annotations=[],
     )

@callback(Output(ids.TASKMAP, 'figure'),
          [Input(ids.BUTTONPLANMOWALL, 'n_clicks'),
           Input(ids.BUTTONCONFIRMSELECTION, 'n_clicks'),
           Input(ids.BUTTONPLANCANCEL, 'n_clicks'),
           Input(ids.MODALSAVECURRENTTASK, 'is_open'),
           Input(ids.MODALREMOVETASK, 'is_open'), 
           Input(ids.DROPDOWNTASKSORDER, 'value'),
           Input(ids.BUTTONREMOVETASK, 'n_clicks'),
           State(ids.TASKMAP, 'selectedData'),])
def update(bpma_nclicks: int, 
           bcs_nclicks: int, 
           bpc_nclicks: int, 
           save_is_open: bool, 
           remove_is_open: bool, 
           tasks_order: list, 
           brt_nclicks: int, 
           selecteddata: dict,
           ) -> list:

    traces = []
    annotation = []
    range_y = [-10, 10]
    rover_position = [robot.position_x, robot.position_y]
    context = ctx.triggered_id
    context_triggered = ctx.triggered

    #Create a task for whole map
    if context == ids.BUTTONPLANMOWALL:# and buttonmowall:
        current_task.preview = pd.DataFrame()
        current_task.selected_perimeter = current_map.perimeter_polygon
        current_map.task_progress = 0
        current_map.total_tasks = 1
        current_map.calculating = True
        route = path.calc(current_task.selected_perimeter, pathplannercfgtask, rover_position)
        if route:
            current_task.calc_route_preview(route) 
        current_map.calculating = False
        current_task.parameters = pathplannercfgtask
        current_task.selection_type = 'perimeter'
        current_task.selection = {'X': [0], 'Y': [0]}

    #Check interactions with graph and create a task for selected zone
    if selecteddata == {'points':[]}: #Workaround for selected data, beacause after select selected data changing to {'poonts':[]} and triggering context_id
        selecteddata = None
    if context == ids.BUTTONCONFIRMSELECTION and selecteddata: #context_triggered[0]['prop_id'] == ids.TASKMAP+'.selectedData' and selecteddata:
        current_task.preview = pd.DataFrame()
        perimeter_preview = current_map.perimeter_polygon
        current_task.selected_perimeter = map.selection(perimeter_preview, selecteddata)
        if not current_task.selected_perimeter.is_empty:
            current_map.task_progress = 0
            current_map.total_tasks = 1
            current_map.calculating = True
            route = path.calc(current_task.selected_perimeter, pathplannercfgtask, rover_position)
            if route:
                current_task.calc_route_preview(route)
            current_map.calculating = False
            current_task.parameters = pathplannercfgtask
            if 'lassoPoints' in selecteddata:
                current_task.selection_type = 'lassoPoints'
                current_task.selection = selecteddata['lassoPoints']
            else:
                current_task.selection_type = 'range'
                current_task.selection = selecteddata['range']

    #Remove preview if cancel button clicked
    if context == ids.BUTTONPLANCANCEL and not current_task.preview.empty:
        current_task.preview = pd.DataFrame()
        annotation = []
    elif context == ids.BUTTONPLANCANCEL:
        current_task.create()
    
    #Load tasks order if selected
    if tasks_order is not None:
        tasks_to_be_done = 0
        current_task.subtasks = pd.DataFrame()
        current_task.subtasks_parameters = pd.DataFrame()
        for task in tasks_order:
            subtasks = tasks.saved[(tasks.saved['name'] == task)&(tasks.saved['map name'] == current_map.name)]
            subtasks_parameters = tasks.saved_parameters[(tasks.saved_parameters['name'] == task)&(tasks.saved_parameters['map name'] == current_map.name)]
            for subtask_nr in subtasks['task nr'].unique():
                subtask = subtasks[subtasks['task nr'] == subtask_nr]
                subtask_parameters = subtasks_parameters[subtasks_parameters['task nr'] == subtask_nr]
                subtask.loc[:, 'task nr'] = tasks_to_be_done
                subtask_parameters.loc[:, 'task nr'] = tasks_to_be_done
                current_task.subtasks = pd.concat([current_task.subtasks, subtask], ignore_index=True)
                current_task.subtasks_parameters = pd.concat([current_task.subtasks_parameters, subtask_parameters], ignore_index=True)
                tasks_to_be_done += 1
    else:
        current_task.subtasks = pd.DataFrame()
        current_task.subtasks_parameters = pd.DataFrame()

    #plot current map
    if not current_map.perimeter.empty:
          coords = current_map.perimeter_for_plot
          #Plot perimeter and exlusions
          coords_filtered = coords.loc[coords['type'] != 'dockpoints']
          range_y = [coords_filtered['Y'].min()-1, coords_filtered['Y'].max()+1]
          for trace in coords_filtered['type'].unique():
               filtered = coords_filtered.loc[coords['type']==trace]
               traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                        name='perimeter', 
                                        mode='lines+markers', 
                                        line=dict(color='#008080'), 
                                        marker=dict(size=1),
                                        hoverinfo='skip')) 

    #plot preview if there
    if not current_task.preview.empty:
        filtered = current_task.preview[current_task.preview['type'] == 'preview route']
        traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], mode='lines', name='preview', opacity=0.7, line=dict(color='#FF0000')))
        annotation = [dict(text='Not saved changes', showarrow=False, xref="paper", yref="paper",x=1,y=1)]
        
    #plot subtasks if there
    index = 0
    preview_color = None
    if not current_task.subtasks.empty and tasks_order != None:
        for task_name in current_task.subtasks['name'].unique():
            color_index = index % len(tasks_color_palette)
            preview_color = tasks_color_palette[color_index]
            for subtask_nr in current_task.subtasks[current_task.subtasks['name'] == task_name]['task nr'].unique():
                filtered = current_task.subtasks[(current_task.subtasks['name'] == task_name) & (current_task.subtasks['task nr'] == subtask_nr) & (current_task.subtasks['type'] == 'preview route')]
                traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], mode='lines', name='subtask', opacity=0.7, line=dict(color=preview_color)))
                index += 1
                
    #Put all annotations together
    annotation.append(dict(text='Map: '+current_map.name, showarrow=False, xref="paper", yref="paper",x=1,y=0))
    
    fig = Patch()
    fig.data = traces
    fig.layout.annotations = annotation

    return fig
