# package imports
import dash
from dash import html

from src.components import ids
from src.components.settings import accordion, modal

dash.register_page(
    __name__,
    path='/settings',
    title='Settings'
)

layout = html.Div(
    [
        html.H4('Settings'),
        html.Div(accordion.accordion_connection),
        html.Div(modal.connection),
        html.Div(modal.mapandposition),
        html.Div(modal.app),
        html.Div(id=ids.SETTINGSHIDDEN)#, style={'display': 'none'}),
    ]
)