from dash import html, Input, Output, State, callback, ctx, clientside_callback
import dash_bootstrap_components as dbc

from . import ids
from src.backend.data.roverdata import robot
from src.backend.data import appdata
from src.backend.data.cfgdata import appcfg

info = dbc.Modal([
                dbc.ModalHeader([
                    dbc.Row([   
                        dbc.Col([
							dbc.ModalTitle('Info'),
						],
                        # style={"flex-grow":"1"}
                        ),   
						dbc.Col([
                            html.I(className="bi bi-moon", style={"margin-right":"0.5rem"}),
							dbc.Switch(
								id="light-switch",
								style={"margin":"0"},
                                value=appcfg.light_mode,
							),
                            html.I(className="bi bi-sun", style={"margin-left":"0.5rem"}),
						],
                        style={"display":"flex", "flex-direction":"row", "align-items":"center"}),   
					])
				]),
                dbc.ModalBody(id=ids.MODALINFOBODY),
                dbc.ModalFooter([
                    html.Div(['CaSSAndRA Version: '+appdata.version], style={'font-size': '10px'})
                ])
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
    
    return html.Div([
            dbc.CardGroup([

				dbc.Card([
					dbc.CardHeader(robot.solution),
					dbc.CardBody([
						html.P(['Acc:', html.Br(), '{}m'.format(robot.position_accuracy)]),
						html.P(['Sat:', html.Br(), '{}'.format(robot.position_visible_satellites_dgps)+'/{}'.format(robot.position_visible_satellites)]),
						html.P(['Age:', html.Br(), robot.position_age_hr]),
						]),
				],
				className="text-center",
				style={"flex":"1"} 
				),
			
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
				style={"flex":"1"}
				),

				dbc.Card([
					dbc.CardHeader('{}%'.format(robot.soc)),
					dbc.CardBody([
						html.P(['Voltage:', html.Br(), '{} V'.format(robot.battery_voltage)]),
						html.P(['Current:', html.Br(), '{} A'.format(robot.amps)]),
						]),
				],
				className="text-center",
				style={"flex":"1"}
				),

            ],
            class_name="d-flex flex-justify-stretch"),
        ])


# Handle light/dark mode
clientside_callback(
    """ 
    (switchOn) => {
       switchOn
         ? document.documentElement.setAttribute('data-bs-theme', 'light')
         : document.documentElement.setAttribute('data-bs-theme', 'dark')
       return window.dash_clientside.no_update
    }
    """,
    Output("light-switch", "id"),
    Input("light-switch", "value"),
)

@callback(Output("light-switch", 'children'),
          [Input("light-switch", 'value')])
def handle_light_switch(value: bool):
    appcfg.light_mode = value
    return []

@callback(Output("light-switch", 'value'),
          [Input(ids.URLUPDATE, 'pathname')])
def update_light_switch_on_reload(pathname: str) -> list:
    return appcfg.light_mode