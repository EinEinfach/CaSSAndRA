# package imports
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd

#local imports
from src.components import ids

dash.register_page(
    __name__,
    path='/taskplanner',
    title='Taskplanner'
)

def update_layout() -> html.Div:
       return html.Div(['Taskplanner'])
            

layout = update_layout()