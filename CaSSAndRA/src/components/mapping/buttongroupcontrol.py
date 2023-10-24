from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

from .. import ids
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import mapping_maps

buttonperimeteradd = dbc.Button(id=ids.BUTTONPERIMETERADD, size='lg', color="success", class_name='bi bi-plus-circle', disabled=False, title='add surface to perimeter', style={"width": "100%"})
buttonperimeterdiff = dbc.Button(id=ids.BUTTONPERIMETERDIFF, size='lg', color="danger", class_name='bi bi-dash-circle', disabled=False, title='remove surface from perimeter', style={"width": "100%"})

buttonhomeadd = dbc.Button(id=ids.BUTTONHOMEADD, size='lg',class_name='me-1 mt-1 mb-1 bi bi-house-add', disabled=False, title='create dockpoints')
buttonsearchwireadd = dbc.Button(id=ids.BUTTONSEARCHWIREADD, size='lg',class_name='me-1 mt-1 mb-1 bi bi-compass', disabled=False, title='create search wire')
buttonaddnewpoint = dbc.Button(id=ids.BUTTONADDNEWPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-plus', disabled=False, title='add new point')
buttondeletelastpoint = dbc.Button(id=ids.BUTTONDELETELASTPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-minus', disabled=False, title='remove last point')
buttonmovepoints= dbc.Button(id=ids.BUTTONMOVEPOINTS, size='lg', class_name='me-1 mt-1 mb-1 bi bi-arrows-move', disabled=False, title='move points')
buttoncancelmapaction = dbc.Button(id=ids.BUTTONCANCELMAPACTION, size='lg', class_name='me-1 mt-1 mb-1 bi bi-x-square-fill', disabled=False, title='cancel selection')

@callback(Output(ids.BUTTONPERIMETERADD, 'disabled'),
          Output(ids.BUTTONPERIMETERDIFF, 'disabled'),
          Output(ids.BUTTONHOMEADD, 'disabled'),
          Output(ids.BUTTONSEARCHWIREADD, 'disabled'),
          Output(ids.BUTTONADDNEWPOINT, 'disabled'),
          Output(ids.BUTTONDELETELASTPOINT, 'disabled'),
          Output(ids.BUTTONFINISHFIGURE, 'disabled'),
          [Input(ids.BUTTONDELETELASTPOINT, 'n_clicks'), 
           Input(ids.BUTTONHOMEADD, 'n_clicks'),
           Input(ids.BUTTONSEARCHWIREADD, 'n_clicks'),
           Input(ids.BUTTONPERIMETERADD, 'n_clicks'),
           Input(ids.BUTTONPERIMETERDIFF, 'n_clicks'),
           Input(ids.MAPPINGMAP, 'figure'),
           State(ids.BUTTONHOMEADD, 'active'),
           State(ids.BUTTONSEARCHWIREADD, 'active'),
           State(ids.BUTTONMOVEPOINTS, 'active')])
def create_figure(bdlp_n_clicks: int, 
                  bha_n_clicks: int, 
                  bswa_n_clicks: int,
                  bpa_n_clicks: int, 
                  bpd_n_clicks: int, 
                  map_figure: dict(), 
                  bha_state: bool,
                  bswa_state: bool,
                  bmp_state: bool
                  ) -> list():
    context = ctx.triggered_id
    #Check if map is loaded
    if mapping_maps.selected == 'from upload' or bmp_state:
        return True, True, True, True, True, True, True
    
    if bha_state:
        create = 'dockpoints'
    elif bswa_state:
        create = 'search wire'
    else:
        create = 'figure'

    if context == ids.BUTTONDELETELASTPOINT:
        mapping_maps.remove_point(create)
    elif context == ids.BUTTONPERIMETERADD:
        mapping_maps.figure_action('add')
    elif context == ids.BUTTONPERIMETERDIFF:
        mapping_maps.figure_action('diff')
        
    state_finish_figure = mapping_maps.is_changed()
    
    if not mapping_maps.build.empty and not mapping_maps.build[mapping_maps.build['type'] == 'edit'].empty:
        return True, True, True, True, False, False, True
    elif not mapping_maps.build.empty:
        if len(mapping_maps.build[mapping_maps.build['type'] == 'figure']) < 3:
            return True, True, False, False, False, False, state_finish_figure
        return False, False, False, False, False, False, state_finish_figure
    return True, True, False, False, False, False, state_finish_figure

@callback(Output(ids.BUTTONHOMEADD, 'active'),
          Output(ids.BUTTONSEARCHWIREADD, 'active'),
          [Input(ids.BUTTONHOMEADD, 'n_clicks'),
          Input(ids.BUTTONSEARCHWIREADD, 'n_clicks'),
          State(ids.BUTTONHOMEADD, 'active'),
          State(ids.BUTTONSEARCHWIREADD, 'active'),
          ])
def home_add_state(bha_n_clicks: int, 
                   bswa_n_clicks: int,
                   bha_state: bool,
                   bswa_state: bool,
                   ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONHOMEADD and not bha_state:
        return True, False
    elif context == ids.BUTTONSEARCHWIREADD and not bswa_state:
        return False, True
    else:
        return False, False

@callback(Output(ids.BUTTONADDNEWPOINT, 'active'),
          [Input(ids.BUTTONADDNEWPOINT, 'n_clicks')])
def add_new_point_state(banp_nclicks: int) -> bool:
    time.sleep(0.5)
    return False

@callback(Output(ids.BUTTONDELETELASTPOINT, 'active'),
          [Input(ids.BUTTONDELETELASTPOINT, 'n_clicks')])
def del_last_point_state(bdlp_nclicks: int) -> bool:
    time.sleep(0.5)
    return False

@callback(Output(ids.BUTTONCANCELMAPACTION, 'active'),
          [Input(ids.BUTTONCANCELMAPACTION, 'n_clicks')])
def cancel_map_action_state(bcma_nclicks: int) -> bool:
    time.sleep(0.5)
    return False

@callback(Output(ids.BUTTONCANCELMAPACTION, 'disabled'),
          [Input(ids.MAPPINGMAP, 'figure')])
def cancel_map_action_disabled(fig: dict) -> bool:
    if mapping_maps.build.empty or (mapping_maps.build[mapping_maps.build['type'] == 'edit'].empty and mapping_maps.build[mapping_maps.build['type'] == 'figure'].empty):
        return True
    else:
        return False

@callback(Output(ids.BUTTONMOVEPOINTS, 'disabled'),
          [Input(ids.MAPPINGMAP, 'figure')])
def update_button_move_points_disabled(figure: dict):
    if mapping_maps.build.empty and not 'shapes' in figure['layout']:
        return True
    else:
        return False

@callback(Output(ids.BUTTONMOVEPOINTS, 'active'),
          [Input(ids.BUTTONMOVEPOINTS, 'n_clicks'),
           State(ids.BUTTONMOVEPOINTS, 'active')])
def update_button_move_points(bmp_nclicks: int, bmp_state: bool):
    context = ctx.triggered_id
    if context == ids.BUTTONMOVEPOINTS and not bmp_state:
        return True
    else:
        False
