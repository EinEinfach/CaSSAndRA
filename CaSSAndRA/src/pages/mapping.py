# package imports
import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

# local imports
from src.components import ids
from src.components.mapping import (
    map,
    uploadsunray,
    modal,
    buttons,
    buttongroupcontrol,
    chooseperimeter,
)

dash.register_page(__name__, path="/mapping", title="Mapping")


def update_layout() -> html.Div:

    # Main column, containing the map and buttons at the bottom
    main_col = dbc.Col(
        [
            html.Div(
                className="loader-wrapper flex-grow-1 p-2",
                children=[
                    dbc.Spinner(
                        delay_show=1000,
                        children=html.Div(
                            [
                                dcc.Graph(
                                    id=ids.MAPPINGMAP,
                                    figure=map.mappingmap,
                                    config={
                                        "displaylogo": False,
                                        "scrollZoom": True,
                                        #'modeBarButtonsToAdd':['eraseshape']
                                    },
                                )
                            ],
                            className="map-graph",
                        ),
                    )
                ],
                style={"overflow": "hidden"},
            ),
            dbc.Row(
                dbc.Col(
                    [
                        html.Div(
                            [
                                buttongroupcontrol.buttonhomeadd,
                                buttongroupcontrol.buttonaddnewpoint,
                                buttongroupcontrol.buttondeletelastpoint,
                                buttongroupcontrol.buttonmovepoints,
                                buttongroupcontrol.buttoncancelmapaction,
                            ],
                            className="text-center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        buttongroupcontrol.buttonperimeteradd
                                    ],
                                    width=6,
                                    md=4,
                                    lg=3,
                                    xxl=2,
                                ),
                                dbc.Col(
                                    [
                                        buttongroupcontrol.buttonperimeterdiff
                                    ],
                                    width=6,
                                    md=4,
                                    lg=3,
                                    xxl=2,
                                ),
                            ],
                            justify="center",
                            align="center",
                            class_name="g-1 p-1"
                        ),
                        dbc.Row(
                            [
                                # column defining the width of the modal button shown on small screens
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            # "Choose Perimeter",
                                            color="info",
                                            size="lg",
                                            id="open-perimeter-modal",
                                            n_clicks=0,
                                            style={"width": "100%"},
                                            class_name="bi bi-card-checklist",
                                        ),
                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle("Choose Perimeter")
                                                ),
                                                dbc.ModalBody(
                                                    chooseperimeter.chooseperimeter
                                                ),
                                                dbc.ModalFooter(
                                                    dbc.Button(
                                                        "Close",
                                                        id="close-perimeter-modal",
                                                        className="ms-auto",
                                                        n_clicks=0,
                                                    )
                                                ),
                                            ],
                                            id="choose-perimeter-modal",
                                            is_open=False,
                                        ),
                                    ],
                                    width=6,
                                    md=4,
                                    lg=3,
                                    xxl=2,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            # "Upload Sunray",
                                            id="open-sunray-modal",
                                            color="info",
                                            size="lg",
                                            class_name="bi bi-cloud-arrow-up-fill",
                                            style={"width": "100%"},
                                        ),
                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle("Upload Sunray")
                                                ),
                                                dbc.ModalBody(
                                                    uploadsunray.uploadsunray
                                                ),
                                                dbc.ModalFooter(
                                                    dbc.Button(
                                                        "Close",
                                                        id="close-sunray-modal",
                                                        className="ms-auto",
                                                        n_clicks=0,
                                                    )
                                                ),
                                            ],
                                            id="upload-sunray-modal",
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
                    ]
                ),
                style={"position": "sticky", "bottom": 0},
            ),
        ],
        class_name="flex-grow-1 d-flex flex-column",
        style={"overflow": "hidden"},
    )

    # Second column that shows the perimeter and sunray selections on larger screen sizes
    sec_col = html.Div(
        [
            dbc.Row(
                [
                    html.Div(
                        [
                            chooseperimeter.chooseperimeter,
                        ],
                        className="text-center",
                    ),
                    html.Div(
                        [
                            uploadsunray.uploadsunray,
                        ],
                        className="text-center",
                    ),
                ],
                justify="evenly",
            ),
        ],
        className="d-none d-sm-none d-md-block",
        style={"width": "330px"},
    )

    # Build the page using the two columns and remaining styles/components required
    return html.Div(
        [
            dbc.Row(
                [
                    main_col,
                    sec_col,
                    modal.sunrayimportstatus,
                    modal.overwriteperimter,
                    modal.newperimeter,
                    modal.selectperimeter,
                    modal.copyperimeter,
                    modal.removeperimeter,
                    modal.finishmapping,
                    modal.nofixsolution,
                    html.Div(id=ids.MAPPINGHIDDEN, style={"display": "none"}),
                ],
                className="flex-nowrap g-0",
                style={"height": "100%"},
            )
        ],
        style={"height": "100%", "width": "100%", "overflow": "hidden"},
    )


layout = update_layout()


# Callback to open/close perimeter selection in modal
@callback(
    Output("choose-perimeter-modal", "is_open"),
    [
        Input("open-perimeter-modal", "n_clicks"),
        Input("close-perimeter-modal", "n_clicks"),
    ],
    [State("choose-perimeter-modal", "is_open")],
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


# Callback to open/close sunray path upload in modal
@callback(
    Output("upload-sunray-modal", "is_open"),
    [
        Input("open-sunray-modal", "n_clicks"),
        Input("close-sunray-modal", "n_clicks"),
    ],
    [State("upload-sunray-modal", "is_open")],
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open
