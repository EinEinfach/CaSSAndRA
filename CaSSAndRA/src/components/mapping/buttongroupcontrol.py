from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import mapping_maps



buttonperimeteradd = dbc.Button(id=ids.BUTTONPERIMETERADD, size='lg', class_name='me-1 mt-1 mb-1 bi bi-plus-circle', disabled=False, title='add surface to perimeter')

buttonperimeterdiff = dbc.Button(id=ids.BUTTONPERIMETERDIFF, size='lg', class_name='me-1 mt-1 mb-1 bi bi-dash-circle', disabled=False, title='remove surface from perimeter')

buttonhomeadd = dbc.Button(id=ids.BUTTONHOMEADD, size='lg',class_name='me-1 mt-1 mb-1 bi bi-house-add', disabled=False, title='create dockpoints')
                
buttonaddnewpoint = dbc.Button(id=ids.BUTTONADDNEWPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-plus', disabled=False, title='add new point')

buttondeletelastpoint = dbc.Button(id=ids.BUTTONDELETELASTPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-minus', disabled=False, title='remove last point')

buttonfinishfigure = dbc.Button(id=ids.BUTTONFINISHFIGURE, size='lg', class_name='me-1 mt-1 mb-1 bi bi-check-square-fill', disabled=False, title='finish and save')

@callback(Output(ids.BUTTONPERIMETERADD, 'disabled'),
          Output(ids.BUTTONPERIMETERDIFF, 'disabled'),
          Output(ids.BUTTONHOMEADD, 'disabled'),
          Output(ids.BUTTONADDNEWPOINT, 'disabled'),
          Output(ids.BUTTONDELETELASTPOINT, 'disabled'),
          Output(ids.BUTTONFINISHFIGURE, 'disabled'),
          [Input(ids.BUTTONADDNEWPOINT, 'n_clicks'),
           Input(ids.BUTTONDELETELASTPOINT, 'n_clicks'), 
           Input(ids.BUTTONHOMEADD, 'n_clicks'),
           Input(ids.BUTTONPERIMETERADD, 'n_clicks'),
           Input(ids.BUTTONPERIMETERDIFF, 'n_clicks'),
           Input(ids.MAPPINGMAP, 'figure'),
           State(ids.BUTTONHOMEADD, 'active')])
def create_figure(banp_n_clicks: int, bdlp_n_clicks: int,
                  bha_n_clicks: int, bpa_n_clicks: int,
                  bpd_n_clicks: int, map_figure: dict(),
                  bha_state: bool) -> list():
    context = ctx.triggered_id
    if mapping_maps.selected == 'from upload':
        return True, True, True, True, True, True
    
    if bha_state:
        create = 'dockpoints'
    else:
        create = 'figure'

    if context == ids.BUTTONADDNEWPOINT:
        mapping_maps.add_point(create)
    elif context == ids.BUTTONDELETELASTPOINT:
        mapping_maps.remove_point(create)
    elif context == ids.BUTTONPERIMETERADD:
        mapping_maps.figure_action('add')
    elif context == ids.BUTTONPERIMETERDIFF:
        mapping_maps.figure_action('diff')
        
    state_finish_figure = mapping_maps.is_changed()
    
    if not mapping_maps.build.empty:
        if len(mapping_maps.build[mapping_maps.build['type'] == 'figure']) < 3:
            return True, True, False, False, False, state_finish_figure
        return False, False, False, False, False, state_finish_figure
    return True, True, False, False, False, state_finish_figure

@callback(Output(ids.BUTTONHOMEADD, 'active'),
          Input(ids.BUTTONHOMEADD, 'n_clicks'),
          State(ids.BUTTONHOMEADD, 'active'))
def home_add_state(bha_n_clicks: int, bha_state: bool) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONHOMEADD:
        return not bha_state
    else:
        return bha_state

