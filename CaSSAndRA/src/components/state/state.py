from dash import html, Input, Output, callback
import dash_bootstrap_components as dbc

from src.backend.data import roverdata
from .. import ids

@callback(Output(ids.STATESTRING, 'children'),
          Input(ids.INTERVAL, 'n_intervals'))
def update(n_intervals: int) -> html.Div():
    current_df = roverdata.calced_from_state.iloc[-1]
    
    #handle the error after start if soc still nan
    if current_df['soc'] is None:
        current_df['soc'] = 0

    #create colors
    if current_df['job'] == 'docking' or current_df['job'] == 'mow' or current_df['job'] == 'go to point' or current_df['job'] == 'charging':
        colorstate = 'success'
        inversestate = True
    elif current_df['job'] == 'docked':
        colorstate = 'light'
        inversestate = False
    elif current_df['job'] == 'idle':
        colorstate = 'warning'
        inversestate = True
    else:
        colorstate = 'danger'
        inversestate = True
    
    if current_df['solution'] == 'fix':
        colorsolution = 'light'
        inversesolution = False
    elif current_df['solution'] == 'float':
        colorsolution = 'warning'
        inversesolution = True
    else:
        colorsolution = 'danger'
        inversesolution = True
    
    if current_df['soc'] > 30:
        colorsoc = 'light'
        inversesoc = False
    elif current_df['soc'] > 15:
        colorsoc = 'warning'
        inversesoc = True
    else:
        colorsoc = 'danger'
        inversesoc = True

    return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Solution'),
                        dbc.CardBody([
                            html.H6(current_df['solution']),
                            ]),
                    ],
                    className="text-center m-1 w-33", 
                    color=colorsolution, inverse=inversesolution
                    ),
                
                ]),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('State'),
                        dbc.CardBody([
                            html.H6(current_df['job']),
                            ]),
                    ],
                    className="text-center m-1 w-33",
                    color=colorstate, inverse=inversestate
                    ),
                ]),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('SoC'),
                        dbc.CardBody([
                            html.H6('{}%'.format(round(current_df['soc']))),
                            ]),
                    ],
                    className="text-center m-1 w-33",
                    color=colorsoc, inverse=inversesoc
                    ),

                ])
            ]),
            
        ])