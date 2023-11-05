# package imports
import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
from datetime import datetime

# local imports
from src.components import ids, modalmowsettings
from src.components.state import map, buttongroupcontrol, state, modal, charts, stats
from src.backend.data.roverdata import robot
from src.backend.data import roverdata

dash.register_page(__name__, path="/", redirect_from=["/state"], title="State")

ENABLE_RIGHT_COL = True # temporary control of right column


def update_layout() -> html.Div:

    # Main Column
    #   This contains the state component, map, and action-bar, containing all buttons
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
								id=ids.STATEMAP,
								figure=map.statemap,
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
            # Sticky positioned row of buttons, forced to always stay at the bottom of the parent container
            dbc.Row(
                [
                    # A container for the two rows of buttons
                    dbc.Col(
                        [
                            # First row of buttons
                            html.Div(
                                [
                                    buttongroupcontrol.buttonhome,
                                    buttongroupcontrol.buttonmowall,
                                    buttongroupcontrol.buttonshortcutselect,
                                    buttongroupcontrol.buttongoto,
                                    buttongroupcontrol.buttonmowsettings,
                                    buttongroupcontrol.buttoncancel,
                                ],
                                className="d-flex justify-content-center flex-wrap p-1",
                            ),
                            # Primary Stop/Go Buttons in second row
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [buttongroupcontrol.buttongo],
                                        width=6,
                                        md=4,
                                        lg=3,
                                        xxl=2,
                                    ),
                                    dbc.Col(
                                        [buttongroupcontrol.buttonstop],
                                        width=6,
                                        md=4,
                                        lg=3,
                                        xxl=2,
                                    ),
                                ],
                                justify="center",
                                align="center",
                                class_name="g-1 p-1",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                color='info',
                                                size='lg',
                                                id=ids.BUTTONOPENMODALCHARTS,
                                                n_clicks=0,
                                                style={'width': '100%'},
                                                class_name='bi bi-graph-up',
                                            ),
                                            dbc.Modal(
                                                [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle('Charts')
                                                ),
                                                dbc.ModalBody(
                                                    id=ids.CONTENTMODALCHARTS,
                                                    style={"padding-top":"0"},
												),
                                                # dbc.ModalFooter([]),
                                            ],
                                            id=ids.MODALCHARTS,
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
                                                color='info',
                                                size='lg',
                                                id=ids.BUTTONOPENMODALSTATS,
                                                n_clicks=0,
                                                style={'width': '100%'},
                                                class_name='bi bi-list-columns',
                                            ),
                                            dbc.Modal(
                                                [
                                                dbc.ModalHeader(
                                                    dbc.ModalTitle('Statistic')
                                                ),
                                                dbc.ModalBody(
                                                    id=ids.CONTENTMODALSTATS,
                                                    style={"padding-top":"0"},
												),
                                            ],
                                            id=ids.MODALSTATS,
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
                        class_name="action-bar",
                    ),
                    modalmowsettings.mowsettings,
                    modal.shortcuts,
                ],
                style={"position": "sticky", "bottom": 0},
            ),
        ],
        className="flex-grow-1 d-flex flex-column",
        style={"height": "100%", "overflow": "hidden"},
    )

    # Second Column
    sec_col = html.Div(
		html.Div(
			charts.chartcontainer + stats.stats,
            style={"width": "100%", "height":"100%", "display":"flex", "flex-direction":"column"},
		),
		className="d-none d-sm-none d-md-block",
		style={"width": "20%", "min-width":"400px", "z-index":"1", "padding-right":"1rem", "padding-bottom":"1rem"},
	)

    # Temporary control of right col
    #   Enabling the right column will show a pre-styled placeholder column that
    #   automatically hides on small screens. If this is enabled and anything
    #   is added to it, then there will need to be alternative ways added to access
    #   that additional content on smaller screens.
    cols = [main_col]
    if ENABLE_RIGHT_COL:
        cols = [main_col, sec_col]

    # Page containing a parent Div and a single row with up to two columns
    #   The second column is configured to be a fixed 330px width, then the main
    #   column uses all the remaining space available. This makes it easy to hide
    #   or show the second column without worrying about breakpoints and provides
    #   a consistent app-like layout
    return html.Div(
        [
            dbc.Row(
                cols,
                className="flex-nowrap g-0",
                style={"height": "100%"},
            ),
			html.Div(id="dummy", style={"display":"none"})
        ],
        style={"height": "100%", "width": "100%", "overflow": "hidden"},
    )


layout = update_layout()

#Deactivate intervall update for state map if selection active
@callback(Output(ids.STATEMAPINTERVAL, 'disabled'),
          [Input(ids.STATEMAP, 'figure'),
           Input(ids.INTERVAL, 'n_intervals'),
           State(ids.STATEMAP, 'figure')
           ])
def interval_enabler(fig: dict,
                     n_intervals: int,
                     fig_state: dict,
                     ) -> bool:
    context = ctx.triggered_id
    if 'selections' in fig_state['layout'] and fig_state['layout']['selections'] != []:
        disable_interval = True
    else:
        disable_interval = False
    return disable_interval
	
# Callback to open/close charts modal
@callback(Output(ids.MODALCHARTS, 'is_open'),
          Output(ids.CONTENTMODALCHARTS, 'children'),
          [Input(ids.BUTTONOPENMODALCHARTS, 'n_clicks'),
           State(ids.MODALCHARTS, 'is_open'),
           ])
def toggle_modal_charts(bom_nclicks: int,
                 is_open: bool,
                 ) -> list:
    if bom_nclicks:
        content = charts.chartcontainer
        return True, content 
    return False, []

# Callback to open/close stats modal
@callback(Output(ids.MODALSTATS, 'is_open'),
          Output(ids.CONTENTMODALSTATS, 'children'),
          [Input(ids.BUTTONOPENMODALSTATS, 'n_clicks'),
           State(ids.MODALSTATS, 'is_open'),
           ])
def toggle_modal_stats(bom_nclicks: int,
                       is_open: bool,
                       ) -> list:
    if bom_nclicks:
        content = stats.statscontainer + stats.stats
        return True, content
    return False, []