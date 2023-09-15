# package imports
import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd

# local imports
from .. components import ids
from src.components.log import cmdinput
from src.backend.data.logdata import commlog

dash.register_page(__name__, path='/log', title='Log')


def update_layout() -> dbc.Container:
    return dbc.Container([
                dbc.Row([
                    dbc.Col(cmdinput.cmdinput),
                    dbc.Col(cmdinput.cmdsend),
                ]),
                dbc.Row([
                    dbc.Table.from_dataframe(commlog.lastdata, 
                                             striped=True, 
                                             bordered=True, 
                                             hover=True,
                                             style = {
                                                #'fontFamily': 'Arial',
                                                'fontSize': '10px',
                                                'textAlign': 'left'
                                            }),
                    # html.Div([
                    #     df.to_string(columns=['content'], header=False, index=False)
                    #     ], style={'whiteSpace': 'pre-wrap'}
                    # )
                ], justify='center', 
                id=ids.LOGTABLE ),
            ])

layout = update_layout()

@callback(Output(ids.LOGTABLE, 'children'),
          Input(ids.INTERVAL, 'n_intervals'))
def update_log_table(n_intervals: int,
                     ) -> dbc.Table():
    commlog.read()
    log = dbc.Table.from_dataframe(commlog.lastdata, 
                                             striped=True, 
                                             bordered=True, 
                                             hover=True,
                                             style = {
                                                #'fontFamily': 'Arial',
                                                'fontSize': '10px',
                                                'textAlign': 'left'
                                            }),
    return log