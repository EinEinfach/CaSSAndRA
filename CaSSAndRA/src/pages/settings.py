# package imports
import dash
from dash import html
import dash_bootstrap_components as dbc

from src.components import ids
from src.components.settings import accordion, modal

dash.register_page(
    __name__,
    path='/settings',
    title='Settings'
)

layout = dbc.Container(
    [
        html.H4('Settings'),
        dbc.Row(accordion.accordion_connection),
        dbc.Row(modal.connection),
        dbc.Row(modal.mapandposition),
        dbc.Row(modal.app),
        html.Div(id=ids.SETTINGSHIDDEN)#, style={'display': 'none'}),
    ],fluid=True
)