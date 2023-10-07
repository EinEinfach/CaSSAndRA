# package imports
import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd

# local imports
from src.components import ids, modaltaskmowsettings
from src.components.tasks import map, buttongroupcontrol, modal, tasksorder

dash.register_page(__name__, path='/taskplanner', title='Taskplanner')


def update_layout() -> html.Div:
    
    main_col = dbc.Col(
        [
            # State module
            dbc.Row(
                dbc.Col(id=ids.STATESTRING, style={"max-width": "500px"}),
                justify="center",
                class_name="p-1"
            ),
            html.Div(
                [
					html.Div(
						[
							dcc.Graph(
								id=ids.TASKMAP,
								figure=map.tasksmap,
								config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': True},
							),
						],
						className="map-graph",
					),
                    html.Div(
                        [
							# Progress-bar
							dbc.Progress(
                                [
                                    dbc.Progress(value=0, bar=True, striped=True, animated=True),
                                    dbc.Progress(value=0, bar=True, striped=True, animated=True, color="goldenrod"),
                                    dbc.Progress(value=0, bar=True, striped=True, animated=True, color="blueviolet"),
                                    dbc.Progress(value=0, bar=True, striped=True, animated=True, color="cornflowerblue"),
                                    dbc.Progress(value=0, bar=True, striped=True, animated=True, color="lightcoral"),
                                    dbc.Progress(value=0, bar=True, striped=True, animated=True, color="lightslategrey"),
								],
                                id=ids.STATEPROGRESSBAR,
                    			value=0, striped=True,
                                animated=True,
                                class_name="progress-bar-hidden",
                                style={"max-width":"500px", "position":"relative", "top":"50%", "margin":"auto", "transform":"translateY(-50%)", "box-shadow":"0 0 1.5rem rgba(0, 0, 0, 0.3)"},
							),
						],
                        id=ids.STATEPROGRESSBARCONTAINER,
                        style={"position":"relative", "width":"100%", "height":"100%", "bottom":"100%", "pointer-events":"none", "padding-left":"3rem", "padding-right":"3rem"},
                        className="progress-bar-container-hidden"
					)
                ],
                className="loader-wrapper flex-grow-1",  # flex grow fills available space
                style={"overflow": "hidden"},  # forces contained map to stay within the container
            ),
            #buttons
            dbc.Row(
                dbc.Col(
                    [
                        # map control buttons
                        html.Div(
                            [
                                buttongroupcontrol.buttonplanmowall,
                                buttongroupcontrol.buttonmowsettings,
                                buttongroupcontrol.buttonconfirmselection,
                                buttongroupcontrol.buttoncancel,
                            ],
                            className='text-center p-1',
                        ),
                        # buttons to open hidden components on mobile devices
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            # 'Order Tasks',
                                            color='info',
                                            size='lg',
                                            id=ids.BUTTONOPENMODALORDERTASKS,
                                            n_clicks=0,
                                            style={'width': '100%'},
                                            class_name='bi bi-list-ol',
                                        ),
                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle('Order Tasks')
                                                ),
                                                dbc.ModalBody(id=ids.CONTENTMODALORDERTASKS),
                                                dbc.ModalFooter([]),
                                            ],
                                            id=ids.MODALORDERTASKS,
                                            is_open=False, centered=True,
                                        ),
                                    ],
                                    width=6,
                                    md=4,
                                    lg=3,
                                    xxl=2,
                                ),
                            ],
                            justify='center',
                            align='center',
                            class_name='g-1 p-1 d-md-none d-lg-none d-xl-none d-xxl-none',
                        ),
                    ],
                    style={'position': 'sticky', 'bottom': 0},
                )
            ),
        ],
        class_name='flex-grow-1 d-flex flex-column',
        style={'overflow': 'hidden'},
    )

    # secondary column (hidden for small and below devices)
    sec_col = html.Div(
        [
            dbc.Row(
                [
                    html.Div(
                        [
                            tasksorder.tasksorder,
                        ],
                        className='text-center',
                    )
                ],
                justify='evenly',
            ),
        ],
        className='d-none d-sm-none d-md-block',
        style={'width': '350px'},
    )

    # build and return the page
    return html.Div(
        [
            dbc.Row(
                [
                    main_col,
                    sec_col,
                    modaltaskmowsettings.mowsettings,
                    modal.savecurrenttask,
                    modal.removecurrenttask,
                    modal.renametask,
                    modal.copytask,
                ],
                className='flex-nowrap g-0',
                style={'height': '100%'},
            )
        ],
        style={'height': '100%', 'width': '100%', 'overflow': 'hidden'},
    )


layout = update_layout()

# Callback to open/close task order selection modal
@callback(Output(ids.MODALORDERTASKS, 'is_open'),
          Output(ids.CONTENTMODALORDERTASKS, 'children'),
          [Input(ids.BUTTONOPENMODALORDERTASKS, 'n_clicks'),
           State(ids.MODALORDERTASKS, 'is_open'),
           ])
def toggle_modal(bom_nclicks: int,
                 is_open: bool,
                 ) -> list:
    if bom_nclicks:
        return True, tasksorder.tasksorder
    return False, dbc.Col()
