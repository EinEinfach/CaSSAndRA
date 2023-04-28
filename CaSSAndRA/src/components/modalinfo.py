from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data import roverdata

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
    current_df = roverdata.state.iloc[-1]
    current_df_from_calc = roverdata.calced_from_state.iloc[-1]
    return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(current_df_from_calc['solution']),
                        dbc.CardBody([
                            html.P(['Acc:', html.Br(), '{}m'.format(round(current_df['position_accuracy'],2))]),
                            html.P(['Sat:', html.Br(), '{}'.format(round(current_df['position_visible_satellites_dgps'],2))+'/{}'.format(round(current_df['position_visible_satellites'],2))]),
                            html.P(['Age:', html.Br(), '{}s'.format(round(current_df['position_age'],2))]),
                            ]),
                    ],
                    className="text-center", 
                    ),
                
                ], ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(current_df_from_calc['job']),
                        dbc.CardBody([
                            html.P(['Pos.', html.Br(), 'x:{}m'.format(round(current_df['position_x'],2)), 
                                    html.Br(), 'y:{}m'.format(round(current_df['position_y'],2))]),
                            html.P(['Tgt.', html.Br(), 'x:{}m'.format(round(current_df['target_x'],2)), 
                                    html.Br(), 'y:{}m'.format(round(current_df['target_y'],2))]),
                            html.P(['Idx:', html.Br(), '{}'.format(current_df['position_mow_point_index'])]),
                            ]),
                    ],
                    className="text-center",
                    ),
  
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader('{}%'.format(round(current_df_from_calc['soc']))),
                        dbc.CardBody([
                            html.P(['Voltage:', html.Br(), '{} V'.format(round(current_df['battery_voltage'],2))]),
                            html.P(['Current:', html.Br(), '{} A'.format(round(current_df['amps'],2))]),
                            ]),
                    ],
                    className="text-center",
                    ),

                )
            ]),
        ])


