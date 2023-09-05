from dash import html, Input, Output, State, callback, ctx
import plotly.graph_objects as go
import pandas as pd

from .. import ids
from src.backend.data import mapdata, calceddata
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import mapping_maps

@callback(Output(ids.MAPPINGMAP, 'figure'),
          [Input(ids.INTERVAL, 'n_intervals'), 
           Input(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
           Input(ids.DROPDOWNSUNRAYIMPORT, 'value'),
           Input(ids.BUTTONPERIMETERADD, 'disabled'),
           Input(ids.MAPPINGMAP, 'selectedData'),
           State(ids.BUTTONHOMEADD, 'active')])
def update(n_intervals: int, selected_perimeter: str(), selected_import: int, 
           bpa_disabled: bool, selecteddata: dict(), bha_state: bool) -> dict():
    
    traces = []
    context = ctx.triggered_id
    context_triggered = ctx.triggered

    if context == ids.DROPDOWNSUNRAYIMPORT and selected_import is not None:
        if not mapping_maps.imported.empty:
            mapping_maps.selected = 'from upload'
            mapping_maps.selected_import = mapping_maps.imported[mapping_maps.imported['map_nr'] == selected_import]
    elif context == ids.DROPDOWNCHOOSEPERIMETER and selected_perimeter is not None:
            mapping_maps.selected = 'from save'
            mapping_maps.select_saved(mapping_maps.saved[mapping_maps.saved['name'] == selected_perimeter])
            #mapping_maps.selected_save = mapping_maps.saved[mapping_maps.saved['name'] == selected_perimeter]

    #check which source is selected
    if mapping_maps.selected == 'from upload':        
        filtered = mapping_maps.selected_import
        line_style = dict(color='#FF0000')
        annotation = [dict(text='From upload (please save first)', showarrow=False, xref="paper", yref="paper",x=1,y=1)]
    elif mapping_maps.selected == 'from save' and mapping_maps.selected_save.equals(mapping_maps.build) or mapping_maps.build.empty:
        filtered = mapping_maps.build
        #filtered = mapping_maps.selected_save
        line_style = dict(color='#008080')
        annotation = []  
    else:
        filtered = mapping_maps.build
        line_style = dict(color='#008080')
        annotation = [dict(text='Not saved changes', showarrow=False, xref="paper", yref="paper",x=1,y=1)]
        # filtered = pd.DataFrame()
        # annotation = []
    if not filtered.empty:
        coords = calceddata.calcmapdata_for_plot(filtered)
        #Plot perimeter and exlusions
        coords_filtered = coords.loc[coords['type'] != 'dockpoints']
        coords_filtered = coords_filtered.loc[coords_filtered['type'] != 'figure']
        for trace in coords_filtered['type'].unique():
            filtered = coords_filtered.loc[coords['type']==trace]
            traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                        name='perimeter', 
                                        mode='lines+markers', 
                                        line=line_style, 
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
        
        #Plot unsaved figure
        filtered = coords.loc[coords['type'] == 'figure']
        traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                name='unsaved figure', 
                                mode='lines+markers', 
                                line=dict(color='#FF0000'), 
                                marker=dict(size=6),
                                hoverinfo='skip'))

    #Check interactions with graph
    if selecteddata == {'points':[]}: #Workaround for selected data, beacause after select selected data changing to {'poonts':[]} and triggering context_id
        selecteddata = None

    if context_triggered[0]['prop_id'] == ids.MAPPINGMAP+'.selectedData' and selecteddata and not bha_state:
        mapping_maps.add_figure(selecteddata)

    #Plot rover position
    traces.append(go.Scatter(x=[robot.position_x], y=[robot.position_y], 
                            mode='markers',
                            name='Rover', 
                            marker = dict(
                                        size=10, 
                                        color='grey', 
                                        symbol='cross-thin-open',
                                        line = dict(width=2, color="DarkSlateGrey")
                                    ),
                            #marker={'size': 12, 'color': 'red'},
                            hoverinfo='skip'
                            )
                    )

    fig = {'data': traces, 
           'layout': go.Layout(
                        yaxis={'scaleratio': 1, 'scaleanchor': 'x',},
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
                                        opacity=0.3,
                                        layer='above')],
                        showlegend=False,
                        uirevision=1,
                        hovermode='closest',
                        dragmode='pan',
                        annotations=annotation
                    )
    }
    
    return fig
            
