# package imports
import dash
from dash import html, dcc, Input, Output, State, callback, ctx
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
from src.backend.data.roverdata import robot

dash.register_page(__name__, path='/mapping', title='Mapping')


def update_layout() -> html.Div:

    # Main column, containing the map and buttons at the bottom
    main_col = dbc.Col(
        [
            # State module
            dbc.Row(
                dbc.Col(id=ids.STATESTRING, style={"max-width": "500px"}),
                justify="center",
                class_name="p-1"
            ),
                        # Map container
            html.Div(
                [
					html.Div(
						[
							dcc.Graph(
								id=ids.MAPPINGMAP,
								figure=map.mappingmap,
								config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': True},
							),
						],
						className="map-graph",
					),
                ],
                className="loader-wrapper flex-grow-1",  # flex grow fills available space
                style={"overflow": "hidden"},  # forces contained map to stay within the container
            ),
            dbc.Row(
                dbc.Col(
                    [
                        html.Div(
                            [
                                buttongroupcontrol.buttonhomeadd,
                                buttongroupcontrol.buttonsearchwireadd,
                                buttongroupcontrol.buttonaddnewpoint,
                                buttongroupcontrol.buttondeletelastpoint,
                                buttongroupcontrol.buttonmovepoints,
                                buttongroupcontrol.buttoncancelmapaction,
                            ],
                            className='text-center',
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
                            justify='center',
                            align='center',
                            class_name='g-1 p-1'
                        ),
                        dbc.Row(
                            [
                                # column defining the width of the modal button shown on small screens
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            # 'Choose Perimeter',
                                            color='info',
                                            size='lg',
                                            id=ids.BUTTONOPENMODALCHOOSEPERIMETER,
                                            n_clicks=0,
                                            style={'width': '100%'},
                                            class_name='bi bi-card-checklist',
                                        ),
                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle('Select map')
                                                ),
                                                dbc.ModalBody([
                                                    dbc.Col(id=ids.CONTENTMODALCHOOSEPERIMETER),
                                                    dbc.ModalFooter([]),
                                                ]),
                                            ],
                                            id=ids.MODALCHOOSEPERIMETER,
                                            is_open=False, centered=True,
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
                                            # 'Upload Sunray',
                                            id=ids.BUTTONOPENMODALUPLOADFILE,
                                            color='info',
                                            size='lg',
                                            class_name='bi bi-cloud-arrow-up-fill',
                                            style={'width': '100%'},
                                        ),
                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle('Import map')
                                                ),
                                                dbc.ModalBody(
                                                    dbc.Col(id=ids.CONETNEMODALUPLOADFILE) 
                                                ),
                                                dbc.ModalFooter([]),
                                            ],
                                            id=ids.MODALUPLOADFILE,
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
                    ]
                ),
                style={'position': 'sticky', 'bottom': 0},
            ),
        ],
        class_name='flex-grow-1 d-flex flex-column',
        style={'overflow': 'hidden'},
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
                        className='text-center',
                    ),
                    html.Div(
                        [
                            uploadsunray.uploadsunray,
                        ],
                        className='text-center',
                    ),
                ],
                justify='evenly',
            ),
        ],
        className='d-none d-sm-none d-md-block',
        style={'width': '400px'},
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
                    modal.renameperimeter,
                    html.Div(id=ids.MAPPINGHIDDEN, style={'display': 'none'}),
                ],
                className='flex-nowrap g-0',
                style={'height': '100%'},
            )
        ],
        style={'height': '100%', 'width': '100%', 'overflow': 'hidden'},
    )


layout = update_layout()

# Callback to open/close perimeter selection in modal
@callback(Output(ids.MODALCHOOSEPERIMETER, 'is_open'),
          Output(ids.CONTENTMODALCHOOSEPERIMETER, 'children'),
          [Input(ids.BUTTONOPENMODALCHOOSEPERIMETER, 'n_clicks'),
           State(ids.MODALCHOOSEPERIMETER, 'is_open')
           ])
def toggle_modal_chooseperimeter(bom_ncliks: int,
                                 is_open: bool
                                 ) -> list():
    if bom_ncliks:
        return not is_open, chooseperimeter.chooseperimeter
    return is_open, dbc.Col()


# Callback to open/close sunray path upload in modal
@callback(Output(ids.MODALUPLOADFILE, 'is_open'),
          Output(ids.CONETNEMODALUPLOADFILE, 'children'),
          [Input(ids.BUTTONOPENMODALUPLOADFILE, 'n_clicks'),
           State(ids.MODALUPLOADFILE, 'is_open')
           ])
def toggle_modal_uploadfile(bom_nclicks: int, 
                            is_open: bool
                            ) -> list():
    if bom_nclicks:
        return not is_open, uploadsunray.uploadsunray
    return is_open, dbc.Col()
    
