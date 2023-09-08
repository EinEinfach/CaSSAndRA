# package imports
import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd

# local imports
from src.components import ids, modaltaskmowsettings
from src.components.tasks import map, buttongroupcontrol, modal, tasksorder

dash.register_page(__name__, path="/taskplanner", title="Taskplanner")


def update_layout() -> html.Div:
    
    main_col = dbc.Col(
        [
            # map
            html.Div(
                className="loader-wrapper flex-grow-1 p-2",
                children=[
                    dbc.Spinner(
                        delay_show=1000,
                        children=html.Div(
                            [
                                dcc.Graph(
                                    id=ids.TASKMAP,
                                    config={"displaylogo": False, "scrollZoom": True},
                                )
                            ],
                            className="map-graph",
                        ),
                    )
                ],
                style={"overflow": "hidden"},
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
                            className="text-center p-1",
                        ),
                        # buttons to open hidden components on mobile devices
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            # "Order Tasks",
                                            color="info",
                                            size="lg",
                                            id="open-order-tasks-modal",
                                            n_clicks=0,
                                            style={"width": "100%"},
                                            class_name="bi bi-list-ol",
                                        ),
                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle("Order Tasks")
                                                ),
                                                dbc.ModalBody(tasksorder.tasksorder),
                                                dbc.ModalFooter(
                                                    dbc.Button(
                                                        "Close",
                                                        id="close-order-tasks-modal",
                                                        className="ms-auto",
                                                        n_clicks=0,
                                                    )
                                                ),
                                            ],
                                            id="order-tasks-modal",
                                            is_open=False,
                                        ),
                                    ],
                                    width=6,
                                    md=4,
                                    lg=3,
                                    xxl=2,
                                ),
                            ],
                            justify="center",
                            align="center",
                            class_name="g-1 p-1 d-md-none d-lg-none d-xl-none d-xxl-none",
                        ),
                    ],
                    style={"position": "sticky", "bottom": 0},
                )
            ),
        ],
        class_name="flex-grow-1 d-flex flex-column",
        style={"overflow": "hidden"},
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
                        className="text-center",
                    )
                ],
                justify="evenly",
            ),
        ],
        className="d-none d-sm-none d-md-block",
        style={"width": "330px"},
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
                className="flex-nowrap g-0",
                style={"height": "100%"},
            )
        ],
        style={"height": "100%", "width": "100%", "overflow": "hidden"},
    )


layout = update_layout()


# Callback to open/close task order selection modal
@callback(
    Output("order-tasks-modal", "is_open"),
    [
        Input("open-order-tasks-modal", "n_clicks"),
        Input("close-order-tasks-modal", "n_clicks"),
    ],
    [State("order-tasks-modal", "is_open")],
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open
