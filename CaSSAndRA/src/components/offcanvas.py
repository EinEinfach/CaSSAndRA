from dash import html, Input, Output, State, callback
import dash_bootstrap_components as dbc

from . import joystick, ids

offcanvas =dbc.Offcanvas([
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader('linear speed'),
                            dbc.CardBody(html.H6(id=ids.LINEAR_SPEED))
                        ], className='text-center mb-2')
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader('angular speed'),
                            dbc.CardBody(html.H6(id=ids.ANGULAR_SPEED))
                        ], className='text-center mb-2')
                    )
                ]),
                dbc.Row(
                    dbc.Col([
                        joystick.joystick
                    ])
                ),
                dbc.Row(
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONFAN, 
                                   class_name='bi bi-fan mt-4', 
                                   color='info', 
                                   size='lg',
                                   title="Start mowing"
                        ), class_name='text-center'
                    ),
                ),
                dbc.Row([
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONSUNRAYOFF, 
                                   class_name='bi bi-lightbulb-off mt-4', 
                                   color='danger', 
                                   size='lg',
                                   title="Shutdown Sunray"
                        ), class_name='text-center'
                    ),
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONSUNRAYREBOOT, 
                                   class_name='bi bi-bootstrap-reboot mt-4', 
                                   color='warning', 
                                   size='lg',
                                   title="Reboot Sunray"
                        ), class_name='text-center'
                    ),
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONGPSREBOOT, 
                                   class_name='bi bi-stars mt-4', 
                                   color='info', 
                                   size='lg',
                                   title="Reboot GPS"
                        ), class_name='text-center'
                    ),
                    #html.Div(id='offcanvas-hidden')
                ])
                ],
                placement='end',
                style={'width': 260},
                id=ids.OFFCANVAS,
                title="Remote control",
                is_open=False,
            )              

@callback(Output(ids.OFFCANVAS, "is_open"),
        Input(ids.OPEN_OFFCANVAS, "n_clicks"),
        [State(ids.OFFCANVAS, "is_open")],)
def toggle_offcanvas(n_clicks: int, is_open: bool) -> bool:
    if n_clicks:
        return not is_open
    return is_open


    