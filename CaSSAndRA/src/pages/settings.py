# package imports
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.components import ids
from src.components.settings import accordion, modal

dash.register_page(
    __name__,
    path='/settings',
    title='Settings'
)

def update_layout() -> html.Div:
    return html.Div([
                html.Div(accordion.accordion_settings),
                html.Div(modal.connection),
                html.Div(modal.mapandposition),
                html.Div(modal.app),
                html.Div(modal.robot),
                html.Div(id=ids.SETTINGSHIDDEN)#, style={'display': 'none'}),
                ]
            )

layout = update_layout()