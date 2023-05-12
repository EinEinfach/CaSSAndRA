from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data.roverdata import robot

info = dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle('Info')),
                dbc.ModalBody(id=ids.MODALINFOBODY),
            ],
            id=ids.MODALINFO, 
            is_open=False,
            size='lg'
        )

@callback(Output(ids.MODALINFO, 'is_open'),
          [Input(ids.BUTTONOPENMODALINFO, 'n_clicks'),
           State(ids.MODALINFO, 'is_open')])
def toggle_modal(n_clicks_bmi: int, modal_is_open: bool) -> bool:
    if n_clicks_bmi:
        return not modal_is_open
    return modal_is_open

@callback(Output(ids.MODALINFOBODY, 'children'),
          [Input(ids.INTERVAL, 'n_intervals')])
def update_modal_body(n_intervals: int) -> html.Div:
    return dbc.Container([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(robot.solution),
                        dbc.CardBody([
                            html.P(['Acc:', html.Br(), '{}m'.format(robot.position_accuracy)]),
                            html.P(['Sat:', html.Br(), '{}'.format(robot.position_visible_satellites_dgps)+'/{}'.format(robot.position_visible_satellites)]),
                            html.P(['Age:', html.Br(), '{}s'.format(robot.position_age)]),
                            ]),
                    ],
                    className="text-center", 
                    ),
                
                ], ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(robot.status),
                        dbc.CardBody([
                            html.P(['Pos.', html.Br(), 'x:{}m'.format(robot.position_x), 
                                    html.Br(), 'y:{}m'.format(robot.position_y)]),
                            html.P(['Tgt.', html.Br(), 'x:{}m'.format(robot.target_x), 
                                    html.Br(), 'y:{}m'.format(robot.target_y)]),
                            html.P(['Idx:', html.Br(), '{}'.format(robot.position_mow_point_index)]),
                            ]),
                    ],
                    className="text-center",
                    ),
  
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader('{}%'.format(robot.soc)),
                        dbc.CardBody([
                            html.P(['Voltage:', html.Br(), '{} V'.format(robot.battery_voltage)]),
                            html.P(['Current:', html.Br(), '{} A'.format(robot.amps)]),
                            ]),
                    ],
                    className="text-center",
                    ),

                )
            ]),
        ],fluid=True)


