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
                html.Div(accordion.accordion_settings, className="accordion-settings-cont"),
                html.Div(modal.connection, className="connection-modal-cont"),
                html.Div(modal.mapandposition, className="map-modal-cont"),
                html.Div(modal.app, className="app-modal-cont"),
                html.Div(modal.robot, className="robot-modal-cont"),
                html.Div(id=ids.SETTINGSHIDDEN, className="settings-hidden-cont")#, style={'display': 'none'}),
                ]
            )

layout = update_layout()