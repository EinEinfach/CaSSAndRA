from dash import html, Input, Output, State, callback, ctx, Patch
import plotly.graph_objects as go
import pandas as pd
from shapely.geometry import Polygon

from icecream import ic

from .. import ids
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import current_map, mapping_maps

mappingmap = go.Figure()
mappingmap.update_layout(
               plot_bgcolor='white',
               yaxis=dict(
                    scaleratio=1, 
                    scaleanchor='x',
                    gridcolor = 'rgba(200, 200, 200, 0.25)',
                    zerolinecolor = 'rgba(200, 200, 200, 0.4)'
                    ),
               xaxis=dict(
                    gridcolor = 'rgba(200, 200, 200, 0.25)',
                    zerolinecolor = 'rgba(200, 200, 200, 0.4)'
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
mappingmap.update_xaxes(nticks=50, ticklabelstep=5,)
mappingmap.update_yaxes(nticks=50, ticklabelstep=5, ticklabelposition="inside")

@callback(Output(ids.MAPPINGMAP, 'figure'),
          Output(ids.MAPPINGINTERVAL, 'disabled'),
           [Input(ids.MAPPINGINTERVAL, 'n_intervals'), 
           Input(ids.URLUPDATE, 'pathname'),
           Input(ids.DROPDOWNCHOOSEPERIMETER, 'value'),
           Input(ids.DROPDOWNSUNRAYIMPORT, 'value'),
           Input(ids.MAPPINGMAP, 'selectedData'),
           Input(ids.MAPPINGMAP, 'clickData'),
           Input(ids.BUTTONMOVEPOINTS, 'active'),
           Input(ids.BUTTONCANCELMAPACTION, 'n_clicks'),
           Input(ids.BUTTONADDNEWPOINT, 'disabled'), #Trigger for remapping after many actions(see buttongroupcontrol.py)
           Input(ids.MODALNOFIXSOLUTION, 'is_open'), #Trigger for remapping after adding a new point(see modal.py)
           State(ids.BUTTONHOMEADD, 'active'),
           State(ids.MAPPINGMAP, 'figure')], prevent_initial_call=True)
def update(n_intervals: int, 
           calledpage: str,
           selected_perimeter: str, 
           selected_import: int,  
           selecteddata: dict, 
           clickdata: dict, 
           bmp_state: bool,
           bcma_nclicks: int,
           banp_state: bool,
           is_open: bool,
           bha_state: bool, 
           fig_state: dict) -> dict:
    traces = []
    annotation = []
    selected_trace = None
    context = ctx.triggered_id
    context_triggered = ctx.triggered
    
    #Check if move points mode -> disable interval
    if bmp_state:
        interval_disabled = True
    else:
        interval_disabled = False

    if 'shapes' in fig_state['layout'] and len(fig_state['layout']['shapes']) == 0:
        del fig_state['layout']['shapes']
    
    #Check if initial call of page or mapping interval still active, reset all changes and remove all shapes
    if context == ids.MAPPINGINTERVAL and (not mapping_maps.legacy_figure.empty or 'shapes' in fig_state['layout']):
        mapping_maps.build = mapping_maps.build_cpy
        mapping_maps.legacy_figure = pd.DataFrame()
        if 'shapes' in fig_state['layout']:
            del fig_state['layout']['shapes']
    
    #Check if a figure was selected
    if context_triggered[0]['prop_id'] == ids.MAPPINGMAP+'.clickData' and clickdata and not bmp_state:
        #remove unfinished figure
        mapping_maps.build = mapping_maps.build[mapping_maps.build['type'] != 'figure']
        #click data
        selected_trace = clickdata['points'][0]['curveNumber']
        selected_point_idx = clickdata['points'][0]['pointIndex']
        selected_name = fig_state['data'][selected_trace]['name']
        #select figure
        #create a copy of build
        mapping_maps.build_cpy = mapping_maps.build
        #check if already a figure select is not edit
        if selected_name != 'edit':
            #check if a edit already exists
            if not mapping_maps.build[mapping_maps.build['type'] == 'edit'].empty:
                mapping_maps.build.loc[:,'type'] = mapping_maps.build['type'].replace(['edit'], mapping_maps.selected_name)
            mapping_maps.selected_name = selected_name
            mapping_maps.build.loc[:,'type'] = mapping_maps.build['type'].replace([selected_name], 'edit')
        #select point
        if selected_point_idx == len(mapping_maps.build[mapping_maps.build['type'] == 'edit']):
            mapping_maps.selected_point = mapping_maps.build[mapping_maps.build['type'] == 'edit'].iloc[[0]]
        else:
            mapping_maps.selected_point = mapping_maps.build[mapping_maps.build['type'] == 'edit'].iloc[[selected_point_idx]]
    
    #Cancel figure selection
    if context == ids.BUTTONCANCELMAPACTION:
        if not mapping_maps.build[mapping_maps.build['type'] == 'figure'].empty:
            mapping_maps.build = mapping_maps.build[mapping_maps.build['type'] != 'figure']
        else:
            mapping_maps.build.loc[:,'type'] = mapping_maps.build['type'].replace(['edit'], mapping_maps.selected_name)
            mapping_maps.selected_point = pd.DataFrame()
    
    #Check if shape selected
    shapes = {}
    if context == ids.BUTTONMOVEPOINTS and bmp_state:
        #remove selection and unfinished figure
        if not mapping_maps.build[mapping_maps.build['type'] == 'figure'].empty:
            mapping_maps.build = mapping_maps.build[mapping_maps.build['type'] != 'figure']
        else:
            mapping_maps.build.loc[:,'type'] = mapping_maps.build['type'].replace(['edit'], mapping_maps.selected_name)
        #create a copy of build
        mapping_maps.build_cpy = mapping_maps.build
        #go ahead with shapes
        data_for_shape = mapping_maps.build
        mapping_maps.legacy_figure = data_for_shape
        for i, geometry_type in enumerate(data_for_shape['type'].unique()):
            coords_to_csv = list(zip(data_for_shape[data_for_shape['type'] == geometry_type]['X'].values.tolist(), data_for_shape[data_for_shape['type'] == geometry_type]['Y'].values.tolist()))
            closedpath = mapping_maps.cartesiantocsv(coords_to_csv, geometry_type)
            shapes.update({geometry_type: dict(type='path', path=closedpath)})
        mapping_maps.build = pd.DataFrame()
        mapping_maps.selected_point = pd.DataFrame()
    elif context == ids.BUTTONMOVEPOINTS and not bmp_state:
        if 'shapes' in fig_state['layout']:
            mapping_maps.build = pd.DataFrame()
            for i, shape in enumerate(fig_state['layout']['shapes']):
                data_for_figure = mapping_maps.csvtocartesian(fig_state['layout']['shapes'][i]['path'])
                data_for_figure['type'] = fig_state['layout']['shapes'][i]['name']
                mapping_maps.build = pd.concat([mapping_maps.build, data_for_figure], ignore_index=True)
            mapping_maps.figure_action('recreate')
            #avoiding of adjustment of last dockpoint, if move tool was used on dockpoints
            mapping_maps.dockpoints = mapping_maps.build[mapping_maps.build['type'] == 'dockpoints']
            mapping_maps.legacy_figure = pd.DataFrame()
        del fig_state['layout']['shapes']


    #Check which dropdown was triggered
    if context == ids.DROPDOWNSUNRAYIMPORT and selected_import is not None:
        if not mapping_maps.imported.empty:
            mapping_maps.selected = 'from upload'
            mapping_maps.selected_import = mapping_maps.imported[mapping_maps.imported['map_nr'] == selected_import]
    elif context == ids.DROPDOWNCHOOSEPERIMETER and selected_perimeter is not None:
            mapping_maps.selected = 'from save'
            mapping_maps.map_old_name = selected_perimeter
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
        coords = mapping_maps.create_perimeter_for_plot(filtered)
        #Plot perimeter and exlusions
        coords_filtered = coords.loc[coords['type'] != 'dockpoints']
        coords_filtered = coords_filtered.loc[coords_filtered['type'] != 'figure']
        for i, trace in enumerate(coords_filtered['type'].unique()):
            filtered = coords_filtered.loc[coords['type']==trace]
            traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                    name=trace, 
                                    mode='lines+markers', 
                                    line=line_style, 
                                    marker=dict(size=3))) 
        #Plot dockpoints
        filtered = coords.loc[coords['type'] == 'dockpoints']
        traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                name='dockpoints', 
                                mode='lines+markers', 
                                line=dict(color='#0f2105'), 
                                marker=dict(size=3)))
        
        #Plot search wire
        filtered = coords.loc[coords['type'] == 'search wire']
        traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'],
                                 name='search wire',
                                 mode='lines+markers',
                                 line=dict(color='#34a123'),
                                 marker=dict(size=3)))
        
        #Plot unsaved figure
        filtered = coords.loc[coords['type'] == 'figure']
        traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                name='unsaved figure', 
                                mode='lines+markers', 
                                line=dict(color='firebrick', dash='dash'), 
                                marker=dict(size=6),
                                hoverinfo='skip'))
        
        #Plot figure to edit
        filtered = coords.loc[coords['type'] == 'edit']
        traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                name='edit figure', 
                                mode='lines+markers', 
                                line=dict(color='#FF0000'), 
                                marker=dict(size=6),
                                hoverinfo='skip'))
  
        #Plot selected point
        filtered = mapping_maps.selected_point
        if not filtered.empty:
            traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'],
                                   mode='markers',
                                   name='selected point',
                                   marker = dict(
                                             size=10, 
                                             color='green', 
                                             symbol='cross-thin-open',
                                             line = dict(width=2, color="DarkSlateGrey")
                                             ),
                                   ))

    #Plot legacy figure  
    if not mapping_maps.legacy_figure.empty:  
        legacy_figure_for_plot = mapping_maps.create_perimeter_for_plot(mapping_maps.legacy_figure)  
        for i, trace in enumerate(legacy_figure_for_plot['type'].unique()):
            filtered = legacy_figure_for_plot.loc[legacy_figure_for_plot['type']==trace]
            traces.append(go.Scatter(x=filtered['X'], y=filtered['Y'], 
                                    name='legacy', 
                                    mode='lines+markers', 
                                    line=dict(color='DarkSlateGrey'), 
                                    marker=dict(size=6),
                                    hoverinfo='skip',
                                    opacity=0.5))

    #Check interactions with graph
    if selecteddata == {'points':[]}: #Workaround for selected data, beacause after select selected data changing to {'poonts':[]} and triggering context_id
        selecteddata = None

    if context_triggered[0]['prop_id'] == ids.MAPPINGMAP+'.selectedData' and selecteddata and not bha_state and not bmp_state:
        mapping_maps.figure_action('recreate')
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
    
    #Create robot image
    robot_img = dict(source=robot.rover_image,
                    xref='x',
                    yref='y',
                    x=robot.position_x,
                    y=robot.position_y,
                    sizex=1.3,
                    sizey=1.3,
                    xanchor='center',
                    yanchor='middle',
                    sizing='contain',
                    opacity=0.3,
                    layer='above')
    
    #Put images together
    imgs = [robot_img]

    #Put all annotations together
    annotation.append(dict(text='Map: '+current_map.name, showarrow=False, xref="paper", yref="paper",x=1,y=0))
    
    fig = Patch()
    fig.data = traces
    fig.layout.images = imgs
    fig.layout.annotations = annotation
    if not "shapes" in fig_state["layout"]:
        fig.layout.shapes.clear()

    if shapes != {}:
        shapes_list = []
        for i, shape in enumerate(shapes):
            shapes_list.append({
                'editable': True,
                'line': {
                    'color': '#FF0000',
                    },
                'name': shape,
                'type': shapes[shape]['type'],
                'path': shapes[shape]['path']
            })
        fig.layout.shapes = shapes_list

    return fig, interval_disabled
            
