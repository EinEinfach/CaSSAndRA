from dash import html, Input, Output, State, callback, ctx
import plotly.graph_objects as go
import pandas as pd

from .. import ids
from src.backend.data import mapdata, roverdata, calceddata
from src.backend.map import map, preview, path


@callback(Output(ids.STATEMAP, 'figure'),
          [Input(ids.INTERVAL, 'n_intervals'),
           #Input(ids.DROPDOWNMAPLINETYPE, 'value'),
           Input(ids.BUTTONHOME, 'n_clicks'),
           Input(ids.BUTTONMOWALL, 'n_clicks'),
           Input(ids.BUTTONZONESELECT, 'n_clicks'),
           Input(ids.BUTTONGOTO, 'n_clicks'),
           Input(ids.BUTTONCANCEL, 'n_clicks'),
           Input(ids.STATEMAP, 'clickData'),
           Input(ids.STATEMAP, 'selectedData'),
           State(ids.BUTTONZONESELECT, 'active'),
           State(ids.BUTTONGOTO, 'active'),
           ])
def update(n_intervals: int, 
           #dropdownmaplinetype: list(), 
           buttonhome: int, buttonmowall: int, 
           buttonzoneselect: int, buttongoto: int,
           buttoncancelclick: int, clickdata: dict(), 
           selecteddata: dict(), buttonzonenselectstate: bool,
           buttongotostate: bool) -> dict():
     
     current_df = roverdata.state.iloc[-1]
     rover_position = [round(current_df['position_x'],2), round(current_df['position_x'],2)] 
     
     context = ctx.triggered_id
     context_triggered = ctx.triggered
     if buttongotostate:
          plotgotopoints = True
     else:
          plotgotopoints = False

     # linetype = None
     # if dropdownmaplinetype == []:
     #      linetype = 'lines'
     # elif len(dropdownmaplinetype) == 2:
     #      linetype = 'lines+markers'
     # else:
     #      linetype = dropdownmaplinetype[0]
    
     mowdata = []
     #Check control buttons state
     if context == ids.BUTTONHOME and buttonhome:
          #What to do, if home button active
          mapdata.gotopoint = pd.DataFrame() 
          mapdata.preview = pd.DataFrame()
          mapdata.mowpath = pd.DataFrame()
          plotgotopoints = False
     elif context == ids.BUTTONMOWALL and buttonmowall:
          mapdata.gotopoint = pd.DataFrame() 
          mapdata.preview = pd.DataFrame()
          mapdata.mowpath = pd.DataFrame()
          mapdata.selected_perimeter = map.create(mapdata.perimeter)
          path.calc(mapdata.mowoffsetstatepage, mapdata.mowanglestatepage, rover_position, mapdata.patternstatepage)
          plotgotopoints = False
     elif context == ids.BUTTONZONESELECT and buttonzoneselect:
          mapdata.gotopoint = pd.DataFrame()
          mapdata.preview = pd.DataFrame()
          mapdata.mowpath = pd.DataFrame()
          plotgotopoints = False
     elif context == ids.BUTTONGOTO and buttongoto:
          mapdata.gotopoint = pd.DataFrame()
          mapdata.preview = pd.DataFrame()
          mapdata.mowpath = pd.DataFrame()
          plotgotopoints = True
     elif context == ids.BUTTONCANCEL:
          mapdata.gotopoint = pd.DataFrame()
          mapdata.preview = pd.DataFrame()
          mapdata.mowpath = pd.DataFrame()
          plotgotopoints = False



     #Check interactions with graph
     if selecteddata == {'points':[]}: #Workaround for selected data, beacause after select selected data changing to {'poonts':[]} and triggering context_id
         selecteddata = None

     if context_triggered[0]['prop_id'] == ids.STATEMAP+'.clickData' and buttongoto:
          preview.gotopoint(clickdata)
     elif context_triggered[0]['prop_id'] == ids.STATEMAP+'.selectedData' and buttonzonenselectstate and selecteddata:
          mapdata.mowpath = pd.DataFrame()
          perimeter_preview = map.create(mapdata.perimeter)
          mapdata.selected_perimeter = map.selection(perimeter_preview, selecteddata)
          path.calc(mapdata.mowoffsetstatepage, mapdata.mowanglestatepage, rover_position, mapdata.patternstatepage)
     
     #Plots
     traces = []
     #calceddata.calcmapdata_for_plot(mapdata.perimeter) 
     if not mapdata.perimeter.empty:
          coords = calceddata.calcmapdata_for_plot(mapdata.perimeter)
          #Plot perimeter and exlusions
          coords_filtered = coords.loc[coords['type'] != 'dockpoints']
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
     
     #Plot invisible goto points
     if plotgotopoints:
          traces.append(go.Scatter(x=mapdata.gotopoints['X'], y=mapdata.gotopoints['Y'], 
                                   mode='markers', 
                                   marker=dict(opacity=0),
                                   hoverinfo='x, y'))
               
     #Plot goto point, if there 
     if not mapdata.gotopoint.empty:  
          current_goto = mapdata.gotopoint.iloc[-1]  
          traces.append(go.Scatter(x=[current_goto['X']], y=[current_goto['Y']],
                                   name='go to', 
                                   mode='markers',
                                   marker = dict(
                                             size=10, 
                                             color='orange', 
                                             symbol='cross',
                                             line = dict(width=2, color="DarkSlateGrey")
                                             ),
                                        )
                                   )
     
     #Plot preview lines or mowpath, if there
     if not mapdata.mowpath.empty:
          filtered = mapdata.mowpath[mapdata.mowpath['type'] == 'way']
          current_mow_idx = current_df['position_mow_point_index'] - 1
          if current_mow_idx < 0:
               current_mow_idx = 0
          path_finished = filtered[filtered.index < current_df['position_mow_point_index']]
          path_to_go = filtered[filtered.index >= current_mow_idx]
          traces.append(go.Scatter(x=path_finished['X'], y=path_finished['Y'], mode='lines', name='mow finished', line=dict(color='#e9e9e9')))
          traces.append(go.Scatter(x=path_to_go['X'], y=path_to_go['Y'], mode='lines', name='mow to go', line=dict(color='#7fb249')))
          mowdata = [dict(text='Distance to go: '+str(mapdata.distancetogo)+'m', showarrow=False, xref="paper", yref="paper",x=1,y=1), 
                     dict(text='Area to mow: '+str(mapdata.areatomow)+'sqm', showarrow=False, xref="paper", yref="paper",x=1,y=0.95)]
     elif not mapdata.preview.empty:
          filtered = mapdata.preview[mapdata.preview['type'] == 'preview route']
          traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], mode='lines', name='preview route', line=dict(color='#7fb249')))

     #Plot rover position
     traces.append(go.Scatter(x=[current_df['position_x']], y=[current_df['position_y'],], 
                             mode='markers',
                             name='Rover', 
                             marker={'size': 12, 'color': 'red'},
                             hoverinfo='skip'
                            )
                    )
     
     #Plot target point
     if current_df['job'] == 4 or current_df['job'] == 1:
          traces.append(go.Scatter(x=[current_df['target_x']], y=[current_df['target_y']],
                                   mode='markers',
                                   name='Target',
                                   marker = dict(
                                             size=10, 
                                             color='green', 
                                             symbol='x',
                                             line = dict(width=2, color="DarkSlateGrey")
                                             ),
                                   ))


     fig = {'data': traces, 
           'layout': go.Layout(yaxis={'scaleratio': 1, 
                                      'scaleanchor': 'x',},
                              margin=dict(
                                        b=20, #bottom margin 40px
                                        l=20, #left margin 40px
                                        r=20, #right margin 20px
                                        t=30, #top margin 20px
                              ),
                              showlegend=False,
                              uirevision=1,
                              hovermode='closest',
                              annotations=mowdata,
                              dragmode='pan'
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
     return fig

# @callback(Output(ids.STATEHIDDEN, 'children'),
#           [Input(ids.INTERVAL, 'n_intervals'),
#            Input(ids.DROPDOWNMAPTRACES, 'value'),
#            Input(ids.DROPDOWNMAPLINETYPE, 'value'),
#            Input(ids.BUTTONHOME, 'n_clicks'),
#            Input(ids.BUTTONMOWALL, 'n_clicks'),
#            Input(ids.BUTTONZONESELECT, 'n_clicks'),
#            Input(ids.BUTTONGOTO, 'n_clicks'),
#            Input(ids.BUTTONCANCEL, 'n_clicks'),
#            Input(ids.STATEMAP, 'clickData'),
#            Input(ids.STATEMAP, 'selectedData'),
#            State(ids.BUTTONZONESELECT, 'active')
#            ])
# def update_hidden(n_intervals: int, dropdownmaptraces: list(), 
#            dropdownmaplinetype: list(), 
#            buttonhome: bool, buttonmowall: bool, 
#            buttonzoneselect: bool, buttongoto: bool,
#            buttoncancelclick: int, 
#            clickData: dict(), 
#            selectedData: dict(),
#            state: bool):
#      context = ctx.triggered_id
#      context_triggered = ctx.triggered
#      return html.Div(str(state))
