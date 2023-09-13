# package imports
import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

# local imports
from src.components import ids, modalmowsettings
from src.components.state import map, buttongroupcontrol, state
from src.backend.data.roverdata import robot

dash.register_page(__name__, path="/", redirect_from=["/state"], title="State")

ENABLE_RIGHT_COL = False  # temporary control of right column


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
                className="loader-wrapper flex-grow-1",  # flex grow fills available space
                children=[
                    dbc.Spinner(
                        delay_show=1000,
                        children=html.Div(
                            [
                                dcc.Graph(
                                    id=ids.STATEMAP,
                                    figure=map.statemap,
                                    config={'displaylogo': False, 'scrollZoom': True},
                                )
                            ],
                            className="map-graph",
                        ),
                    )
                ],
                style={
                    "overflow": "hidden"
                },  # forces contained map to stay within the container
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
                                    buttongroupcontrol.buttonzoneselect,
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
                        ],
                        class_name="action-bar",
                    ),
                    modalmowsettings.mowsettings,
                ],
                style={"position": "sticky", "bottom": 0},
            ),
        ],
        className="flex-grow-1 d-flex flex-column",
        style={"height": "100%", "overflow": "hidden"},
    )

    # Second Column
    #   This contains a placeholder card and the pre-existing hidden state modules
    sec_col = html.Div(
        [
            dbc.Row(
                [
                    # Add components to second column here and remove placeholders
                    dbc.Card(
                        [dbc.CardHeader("Placeholder"), dbc.CardBody("Placeholder")],
                        class_name="text-center",
                    ),
                    html.Div(id=ids.STATEHIDDEN, style={"display": "none"}),
                    html.Div(id=ids.STATEHIDDEN2, style={"display": "none"}),
                    html.Div(id=ids.STATEHIDDEN3, style={"display": "none"}),
                ],
                justify="evenly",
                class_name="g-0 p-1",
            ),
        ],
        className="d-none d-sm-none d-md-block",
        style={"width": "330px"},
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
            )
        ],
        style={"height": "100%", "width": "100%", "overflow": "hidden"},
    )


layout = update_layout()

#Workarround to deactivate and activate interval call for map on state page. For some reason ids.URLUPDATE doesn't fire a callback for map.
@callback(Output(ids.STATEMAPINTERVAL, 'disabled'),
          [Input(ids.URLUPDATE, 'pathname'),
           Input(ids.INTERVAL, 'n_intervals'),
           Input(ids.STATEMAPINTERVAL, 'n_intervals'),
           State(ids.URLUPDATE, 'pathname'),
           State(ids.STATEMAPINTERVAL, 'disabled'),
           ])
def interval_enabler(calledpage: str,
                     n_intervals: int,
                     n_intervals_statemap: int,
                     currentpage: str,
                     state_n_intervals_state: bool,
                     ) -> bool:
    context = ctx.triggered_id
    if context == ids.URLUPDATE and currentpage == '/':
        disable_interval = False
    elif context == ids.STATEMAPINTERVAL and robot.job == 2:
        disable_interval = True
    elif context == ids.INTERVAL and robot.job != 2:
        disable_interval = False
    else:
        disable_interval = state_n_intervals_state
    return disable_interval

