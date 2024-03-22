from dash import html, Input, Output, State, callback, ctx, Patch
import plotly.graph_objects as go
import pandas as pd

from .. import ids
from src.backend.data import mapdata, calceddata
from src.backend.data.mapdata import current_map, current_task, tasks, progress_color_palette, tasks_color_palette
from src.backend.map import map, path
from src.backend.data.roverdata import robot
from src.backend.data.cfgdata import pathplannercfgstate

statemap = go.Figure()
statemap.update_layout(
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
               selections=[],
     )

@callback(Output('dummy', 'children'),
          [          
            Input(ids.BUTTONHOME, 'n_clicks'),
            Input(ids.BUTTONMOWALL, 'n_clicks'),
            Input(ids.DROPDOWNSHORTCUTS, 'value'),
            Input(ids.BUTTONGOTO, 'n_clicks'),
            Input(ids.STATEMAP, 'clickData'),
            Input(ids.STATEMAP, 'selectedData'),
            Input(ids.BUTTONCANCEL, 'n_clicks'),
            State(ids.BUTTONGOTO, 'active'),
            State(ids.STATEMAP, 'figure'),
        ], prevent_initial_call=True)
def handle_buttons(
            buttonhome: int, 
            buttonmowall: int, 
            tasks_order: list,
            buttongoto: int,
            clickdata: dict, 
            selecteddata: dict,
            buttoncancelclick: int,
            buttongotostate: bool, 
            fig_state: dict,
        ) -> str: 
    
     context = ctx.triggered_id
     context_triggered = ctx.triggered
     rover_position = [robot.position_x, robot.position_y] 

     #Check interactions with graph
     if selecteddata == {'points':[]}: #Workaround for selected data, beacause after select selected data changing to {'poonts':[]} and triggering context_id
          selecteddata = None
     if context_triggered[0]['prop_id'] == ids.STATEMAP+'.clickData' and buttongoto:
          current_map.set_gotopoint(clickdata)

     if buttongotostate:
          current_map.plotgotopoints = True
     else:
          current_map.plotgotopoints = False
     
     if context == ids.BUTTONHOME and buttonhome:
          #What to do, if home button active
          current_map.gotopoint = pd.DataFrame() 
          current_map.preview = pd.DataFrame()
          current_task.subtasks = pd.DataFrame()
          current_task.subtasks_parameters = pd.DataFrame()
          #current_map.mowpath = pd.DataFrame()
          current_map.plotgotopoints = False
     elif context == ids.BUTTONMOWALL and buttonmowall:
          current_map.gotopoint = pd.DataFrame() 
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
          current_task.subtasks = pd.DataFrame()
          current_task.subtasks_parameters= pd.DataFrame()
          if 'selections' in fig_state['layout'] and fig_state['layout']['selections'] != []:
               current_map.selected_perimeter = map.selection(current_map.perimeter_polygon, selecteddata)
          else:
               current_map.selected_perimeter = current_map.perimeter_polygon
          current_map.calculating = True
          current_map.task_progress = 0
          current_map.total_tasks = 1
          route = path.calc(current_map.selected_perimeter, pathplannercfgstate, rover_position)
          if route:
               current_map.areatomow = round(current_map.selected_perimeter.area)
               current_map.calc_route_preview(route) 
          current_map.calculating = False
          current_map.plotgotopoints = False
     elif context == ids.DROPDOWNSHORTCUTS and tasks_order != None:
          #Load tasks order if selected
          current_map.gotopoint = pd.DataFrame() 
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
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
          current_map.plotgotopoints = False
     elif context == ids.BUTTONGOTO and buttongoto:
          current_map.gotopoint = pd.DataFrame()
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
          current_task.subtasks = pd.DataFrame()
          current_task.subtasks_parameters = pd.DataFrame()
          current_map.plotgotopoints = True
     elif context == ids.BUTTONCANCEL:
          if not current_map.obstacles.empty:
               current_map.obstacles = pd.DataFrame()
          else:
               current_map.gotopoint = pd.DataFrame()
               current_map.preview = pd.DataFrame()
               current_map.mowpath = pd.DataFrame()
               current_task.subtasks = pd.DataFrame()
               current_task.subtasks_parameters = pd.DataFrame()
               current_map.plotgotopoints = False

     return str()
    
@callback(Output(ids.STATEMAP, 'figure'),
        [
            Input(ids.STATEMAPINTERVAL, 'n_intervals'),
            Input(ids.URLUPDATE, 'pathname'),
            Input('dummy', 'children'),
        ], prevent_initial_call = True)
def update(n_intervals: int,
           calledpage: str,
           buttoncall: str,
           ) -> Patch:
     mowdata = []
     #Plots
     traces = []
     #calceddata.calcmapdata_for_plot(mapdata.perimeter) 
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
          #Plot dockpoints
          filtered = coords.loc[coords['type'] == 'dockpoints']
          traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                   name='dockpoints', 
                                   mode='lines+markers', 
                                   line=dict(color='#0f2105'), 
                                   marker=dict(size=3),
                                   hoverinfo='skip'))
     
     #Plot invisible goto points
     if current_map.plotgotopoints:
          traces.append(go.Scatter(x=current_map.gotopoints['X'], y=current_map.gotopoints['Y'], 
                                   mode='markers', 
                                   marker=dict(opacity=0),
                                   hoverinfo='x, y'))
               
     #Plot goto point, if there 
     if not current_map.gotopoint.empty:  
          current_goto = current_map.gotopoint.iloc[-1]  
          traces.append(go.Scatter(x=[current_goto['X']], y=[current_goto['Y']],
                                   name='go to', 
                                   mode='markers',
                                   marker = dict(
                                             size=10, 
                                             color='orange', 
                                             symbol='x-thin-open',
                                             line = dict(width=2, color="DarkSlateGrey")
                                             ),
                                        )
                                   )
     
     #Plot preview lines or mowpath, if there
     if not current_map.mowpath.empty:
          filtered = current_map.mowpath[current_map.mowpath['type'] == 'way']
          current_mow_idx = robot.position_mow_point_index - 1
          if current_mow_idx < 0:
               current_mow_idx = 0
          path_finished = filtered[filtered.index < robot.position_mow_point_index]
          path_to_go = filtered[filtered.index >= current_mow_idx]
          #calc mow progress
          mow_progress = calceddata.calc_mow_progress(current_map.mowpath, current_mow_idx)
          traces.append(go.Scatter(x=path_finished['X'], y=path_finished['Y'], mode='lines', name='mow finished', opacity=0.5, line=dict(color='rgba(127, 127, 127, 0.25)')))
          traces.append(go.Scatter(x=path_to_go['X'], y=path_to_go['Y'], mode='lines', name='mow to go', opacity=0.7, line=dict(color='#7fb249')))
          mowdata = [dict(text='Distance: '+str(mow_progress[0])+'m/'+str(mow_progress[1])+'m ('+str(mow_progress[2])+'%)', showarrow=False, xref="paper", yref="paper",x=1,y=1),
                         dict(text='Index: '+str(mow_progress[3])+'/'+str(mow_progress[4])+' ('+str(mow_progress[5])+'%)', showarrow=False, xref="paper", yref="paper",x=1,y=0.95), 
                         dict(text='Area to mow: '+str(current_map.areatomow)+'sqm', showarrow=False, xref="paper", yref="paper",x=1,y=0.9)]
          robot.mowprogress = round(mow_progress[5]/100, 3)
     elif not current_map.preview.empty:
          filtered = current_map.preview[current_map.preview['type'] == 'preview route']
          traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], mode='lines', name='preview route', opacity=0.7, line=dict(color='#7fb249')))
     elif not current_task.subtasks.empty:
          index = 0
          for task_name in current_task.subtasks['name'].unique():
               color_index = index % len(tasks_color_palette)
               preview_color = tasks_color_palette[color_index]
               task_to_plot = current_task.subtasks[current_task.subtasks['name'] == task_name]
               for subtask in task_to_plot['task nr'].unique():
                    filtered = task_to_plot[(task_to_plot['task nr'] == subtask)&(task_to_plot['type'] == 'preview route')]
                    traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], mode='lines', name='preview route', opacity=0.7, line=dict(color=preview_color))) 
                    index += 1

     #Plot obstacles if there
     imgs = []
     if not current_map.obstacles.empty:
          obstacles = current_map.obstacles
          for obstacle in obstacles['CRC'].unique():
               filtered = obstacles[obstacles['CRC']==obstacle]
               filtered = filtered[filtered['type'] != 'center']
               traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                        name='obstacle', 
                                        mode='lines', 
                                        line=dict(color='#FF6600'), 
                                        fill='toself',
                                        hoverinfo='skip')) 
               obstacle_center_coords = obstacles[(obstacles['CRC']==obstacle)&(obstacles['type']=='center')]
               obstacle_x = obstacle_center_coords.iloc[0]['X']
               obstacle_y = obstacle_center_coords.iloc[0]['Y']

     #Plot target point
     if robot.job == 4 or robot.job == 1:
          traces.append(go.Scatter(x=[robot.target_x], y=[robot.target_y],
                                   mode='markers',
                                   name='Target',
                                   marker = dict(
                                             size=10, 
                                             color='green', 
                                             symbol='cross-thin-open',
                                             line = dict(width=2, color="DarkSlateGrey")
                                             ),
                                   ))
     
     #Create robot image
     robot_img = dict(
                    source=robot.rover_image,
                    xref='x',
                    yref='y',
                    x=robot.position_x,
                    y=robot.position_y,
                    sizex=1.3,
                    sizey=1.3,
                    xanchor='center',
                    yanchor='middle',
                    sizing='contain',
                    opacity=1,
                    layer='above')
     
     #Put all images together
     imgs.append(robot_img)

     #Put all annotations together
     mowdata.append(dict(text='Map: '+current_map.name, showarrow=False, xref="paper", yref="paper",x=1,y=0))

     fig = Patch()
     fig.data = traces
     fig.layout.images = imgs
     fig.layout.annotations = mowdata
     if robot.job == 1:
          fig.layout.selections = []
     
     return fig
