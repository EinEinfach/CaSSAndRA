from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import current_map
                
buttonplanmowall = dbc.Button(id=ids.BUTTONPLANMOWALL, size='lg', class_name='me-1 mt-1 bi bi-map-fill', disabled=False, title='plan mow all')
buttonmowsettings = dbc.Button(id=ids.BUTTONPLANMOWSETTINGS, size='lg', class_name='me-1 mt-1 bi bi-gear-fill', disabled=False, title='temporarly mow settings')
buttonconfirmselection = dbc.Button(id=ids.BUTTONCONFIRMSELECTION, size='lg', class_name='me-1 mt-1 bi bi-check-square-fill', disabled=False, title='confirm selection')
buttoncancel = dbc.Button(id=ids.BUTTONPLANCANCEL, size='lg', class_name='me-1 mt-1 bi bi-x-square-fill', disabled=False, title='cancel')

