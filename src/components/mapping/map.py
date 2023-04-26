from dash import html, Input, Output, State, callback, ctx
import plotly.graph_objects as go
import pandas as pd

from .. import ids
from src.backend.data import mapdata, calceddata

@callback(Output(ids.MAPPINGMAP, 'figure'),
          [Input(ids.DROPDOWNSUNRAYIMPORT, 'value')])
def update(map_nr: int) -> dict():
    traces = []
    context = ctx.triggered_id
    if context == ids.DROPDOWNSUNRAYIMPORT and map_nr is not None:
        if not mapdata.imported.empty:
            filtered = mapdata.imported[mapdata.imported['map_nr'] == map_nr]
            coords = calceddata.calcmapdata_for_plot(filtered)
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
    fig = {'data': traces, 
           'layout': go.Layout(
                        yaxis={'scaleratio': 1, 'scaleanchor': 'x',},
                        margin=dict(
                                    b=20, #bottom margin 40px
                                    l=20, #left margin 40px
                                    r=20, #right margin 20px
                                    t=30, #top margin 20px
                        ),
                        showlegend=False,
                        uirevision=1,
                        hovermode='closest',
                        dragmode='pan'
                    )
    }
    
    return fig
            
