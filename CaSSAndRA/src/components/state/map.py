from dash import html, Input, Output, State, callback, ctx
import plotly.graph_objects as go
import pandas as pd

from .. import ids
from src.backend.data import mapdata, calceddata
from src.backend.data.mapdata import current_map
from src.backend.map import map, path
from src.backend.data.roverdata import robot
from src.backend.data.cfgdata import pathplannercfgstate


@callback(Output(ids.STATEMAP, 'figure'),
          Output(ids.INTERVAL, 'disabled', allow_duplicate=True),
          [Input(ids.INTERVAL, 'n_intervals'),
           Input(ids.BUTTONHOME, 'n_clicks'),
           Input(ids.BUTTONMOWALL, 'n_clicks'),
           Input(ids.BUTTONZONESELECT, 'n_clicks'),
           Input(ids.BUTTONGOTO, 'n_clicks'),
           Input(ids.BUTTONCANCEL, 'n_clicks'),
           Input(ids.STATEMAP, 'clickData'),
           Input(ids.STATEMAP, 'selectedData'),
           State(ids.BUTTONZONESELECT, 'active'),
           State(ids.BUTTONGOTO, 'active'),
           ], prevent_initial_call=True)
def update(n_intervals: int,
           buttonhome: int, buttonmowall: int, 
           buttonzoneselect: int, buttongoto: int,
           buttoncancelclick: int, clickdata: dict(), 
           selecteddata: dict(), buttonzonenselectstate: bool,
           buttongotostate: bool) -> dict():
     rover_position = [robot.position_x, robot.position_y] 

     context = ctx.triggered_id
     context_triggered = ctx.triggered
     if buttongotostate:
          plotgotopoints = True
     else:
          plotgotopoints = False

     mowdata = []
     #Check control buttons state
     if context == ids.BUTTONHOME and buttonhome:
          #What to do, if home button active
          current_map.gotopoint = pd.DataFrame() 
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
          plotgotopoints = False
     elif context == ids.BUTTONMOWALL and buttonmowall:
          current_map.gotopoint = pd.DataFrame() 
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
          mapdata.selected_perimeter = current_map.perimeter_polygon
          path.calc(pathplannercfgstate, rover_position)
          plotgotopoints = False
     elif context == ids.BUTTONZONESELECT and buttonzoneselect:
          current_map.gotopoint = pd.DataFrame()
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
          plotgotopoints = False
     elif context == ids.BUTTONGOTO and buttongoto:
          current_map.gotopoint = pd.DataFrame()
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
          plotgotopoints = True
     elif context == ids.BUTTONCANCEL:
          current_map.gotopoint = pd.DataFrame()
          current_map.preview = pd.DataFrame()
          current_map.mowpath = pd.DataFrame()
          plotgotopoints = False



     #Check interactions with graph
     if selecteddata == {'points':[]}: #Workaround for selected data, beacause after select selected data changing to {'poonts':[]} and triggering context_id
         selecteddata = None

     if context_triggered[0]['prop_id'] == ids.STATEMAP+'.clickData' and buttongoto:
          current_map.set_gotopoint(clickdata)
     elif context_triggered[0]['prop_id'] == ids.STATEMAP+'.selectedData' and buttonzonenselectstate and selecteddata:
          current_map.mowpath = pd.DataFrame()
          perimeter_preview = current_map.perimeter_polygon
          mapdata.selected_perimeter = map.selection(perimeter_preview, selecteddata)
          path.calc(pathplannercfgstate, rover_position)
     
     #Plots
     traces = []
     #calceddata.calcmapdata_for_plot(mapdata.perimeter) 
     if not current_map.perimeter.empty:
          coords = current_map.perimeter_for_plot
          #Plot perimeter and exlusions
          coords_filtered = coords.loc[coords['type'] != 'dockpoints']
          range_x = [coords_filtered['X'].min()-1, coords_filtered['X'].max()+1]
          range_y = [coords_filtered['Y'].min()-1, coords_filtered['Y'].max()+1]
          for trace in coords_filtered['type'].unique():
               filtered = coords_filtered.loc[coords['type']==trace]
               traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                        name='perimeter', 
                                        mode='lines+markers', 
                                        line=dict(color='#008080'), 
                                        marker=dict(size=3),
                                        hoverinfo='skip')) 
          #Plot dockpoints
          filtered = coords.loc[coords['type'] == 'dockpoints']
          traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                   name='dockpoints', 
                                   mode='lines+markers', 
                                   line=dict(color='#0f2105'), 
                                   marker=dict(size=3),
                                   hoverinfo='skip'))
     else:
          range_x = [-10, 10]
          range_y = [-10, 10]
     
     #Plot invisible goto points
     if plotgotopoints:
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
          traces.append(go.Scatter(x=path_finished['X'], y=path_finished['Y'], mode='lines', name='mow finished', opacity=0.5, line=dict(color='#e9e9e9')))
          traces.append(go.Scatter(x=path_to_go['X'], y=path_to_go['Y'], mode='lines', name='mow to go', opacity=0.7, line=dict(color='#7fb249')))
          mowdata = [dict(text='Distance: '+str(mow_progress[0])+'m/'+str(mow_progress[1])+'m ('+str(mow_progress[2])+'%)', showarrow=False, xref="paper", yref="paper",x=1,y=1),
                     dict(text='Index: '+str(mow_progress[3])+'/'+str(mow_progress[4])+' ('+str(mow_progress[5])+'%)', showarrow=False, xref="paper", yref="paper",x=1,y=0.95), 
                     dict(text='Area to mow: '+str(current_map.areatomow)+'sqm', showarrow=False, xref="paper", yref="paper",x=1,y=0.9)]
     elif not current_map.preview.empty:
          filtered = current_map.preview[current_map.preview['type'] == 'preview route']
          traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], mode='lines', name='preview route', opacity=0.7, line=dict(color='#7fb249')))

     #Plot rover position
     # traces.append(go.Scatter(x=[robot.position_x], y=[robot.position_y], 
     #                         mode='markers',
     #                         name='Rover', 
     #                         marker={'size': 12, 'color': 'red'},
     #                         hoverinfo='skip'
     #                        )
     #                )
     
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


     fig = {'data': traces, 
           'layout': go.Layout(yaxis=dict(range=range_y, scaleratio=1, scaleanchor='x'),
                               xaxis=dict(range=range_x),
                               margin=dict(
                                        b=20,  #bottom margin
                                        l=20,  #left margin
                                        r=5,   #right margin
                                        t=30,  #top margin
                              ),
                              images=[
                                   dict(source=robot.rover_image,
                                        xref='x',
                                        yref='y',
                                        x=robot.position_x,
                                        y=robot.position_y,
                                        sizex=0.8,
                                        sizey=0.8,
                                        xanchor='center',
                                        yanchor='middle',
                                        sizing='contain',
                                        opacity=1,
                                        layer='above')],
                              showlegend=False,
                              uirevision=1,
                              hovermode='closest',
                              annotations=mowdata,
                              dragmode='pan',
                              #autosize=True
                              #title='Map', 
                              #xaxis={'range': [range_min, range_max]},
                              #yaxis={'range': [range_min, range_max], 'scaleratio': 1, 'scaleanchor': 'x'},
                              #width=700,
                              #height=300,
                              #showlegend=False,
                              #uirevision=1,
                              #paper_bgcolor='rgba(0,0,0,0)',
                              #plot_bgcolor='rgba(0,0,0,0)'
                            )}       
     # fig = go.Figure()
     # fig.add_traces(traces) 
     # fig.update_layout(
     #                yaxis={'scaleratio': 1, 'scaleanchor': 'x',},
     #                margin=dict(
     #                          b=20, #bottom margin 40px
     #                          l=20, #left margin 40px
     #                          r=20, #right margin 20px
     #                          t=30, #top margin 20px
     #                          ),
     #                showlegend=False,
     #                uirevision=1,
     #                hovermode='closest',
     #                #paper_bgcolor='rgba(0,0,0,0)',
     #                #plot_bgcolor='rgba(0,0,0,0)'
     #                )            
     return fig, False