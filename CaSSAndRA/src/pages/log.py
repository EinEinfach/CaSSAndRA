# package imports
import dash
from dash import html, dcc, Input, Output, State, callback, ctx
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
                    dbc.Col(cmdinput.cmdinput, style={"flex" : "1 0 0%"}),
                    dbc.Col(cmdinput.cmdsend, style={"flex" : "0 0 0%"}),
                    dbc.Col(cmdinput.logpaused, style={"flex" : "0 0 0%"}),
                ], style={"padding" : "0.5rem 10%"}),
                dbc.Row([
                    dbc.Table.from_dataframe(commlog.lastdata, 
                                             striped=True, 
                                             bordered=True, 
                                             hover=True,
                                             class_name="log_table"),
                    # html.Div([
                    #     df.to_string(columns=['content'], header=False, index=False)
                    #     ], style={'whiteSpace': 'pre-wrap'}
                    # )
                ], justify='center', style={'flex': 'auto', 'overflow-y': 'scroll'}, 
                id=ids.LOGTABLE ),
            ], style={"height" : "100%", "overflow" : "hidden", "display" : "flex", "flex-direction" : "column"})

layout = update_layout()

@callback(Output(ids.LOGTABLE, 'children'),
          Input(ids.LOGINTERVAL, 'n_intervals'))
def update_log_table(n_intervals: int,
                     ) -> dbc.Table():
    commlog.read()
    log = dbc.Table.from_dataframe(commlog.lastdata, 
                                             striped=True, 
                                             bordered=True, 
                                             hover=True,
                                             class_name="log_table"),
    return log

@callback(Output(ids.LOGINTERVAL, 'disabled'),
          [Input(ids.URLUPDATE, 'pathname'),
           Input(ids.BUTTONLOGPAUSED, 'active'),
           ])
def interval_enabler(calledpage: str,
                     blp_active: bool,
                     ) -> bool:
    context = ctx.triggered_id
    if blp_active:
        return True
    else:
        return False