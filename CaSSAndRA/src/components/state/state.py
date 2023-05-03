from dash import html, Input, Output, callback
import dash_bootstrap_components as dbc

from src.backend.data.roverdata import robot
from .. import ids

@callback(Output(ids.STATESTRING, 'children'),
          Input(ids.INTERVAL, 'n_intervals'))
def update(n_intervals: int) -> html.Div():

    #create colors
    if robot.status == 'docking' or robot.status == 'mow' or robot.status == 'transit' or robot.status == 'charging':
        colorstate = 'success'
        inversestate = True
    elif robot.status == 'docked':
        colorstate = 'light'
        inversestate = False
    elif robot.status == 'idle':
        colorstate = 'warning'
        inversestate = True
    else:
        colorstate = 'danger'
        inversestate = True
    
    if robot.solution == 'fix':
        colorsolution = 'light'
        inversesolution = False
    elif robot.solution == 'float':
        colorsolution = 'warning'
        inversesolution = True
    else:
        colorsolution = 'danger'
        inversesolution = True
    
    if robot.soc > 30:
        colorsoc = 'light'
        inversesoc = False
    elif robot.soc > 15:
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
                            html.H6(robot.solution),
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
                            html.H6(robot.status),
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
                            html.H6('{}%'.format(robot.soc)),
                            ]),
                    ],
                    className="text-center m-1 w-33",
                    color=colorsoc, inverse=inversesoc
                    ),

                ])
            ]),
            
        ])