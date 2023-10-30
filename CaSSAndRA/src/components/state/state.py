from dash import html, Input, Output, State, callback
import dash_bootstrap_components as dbc

from src.backend.data.roverdata import robot
from .. import ids

CARD_STYLES = {"width": "33%", "margin-bottom": "0"}
CARD_BODY_CLASSES = "d-flex flex-column justify-content-center stateCardBody"


@callback(Output(ids.STATESTRING, "children"), Input(ids.INTERVAL, "n_intervals"))
def update(n_intervals: int) -> dbc.Row:
    # create colors
    if (
        robot.status == "docking"
        or robot.status == "mow"
        or robot.status == "transit"
        or robot.status == "charging"
    ):
        colorstate = "success"
        inversestate = True
    elif robot.status == "docked":
        colorstate = "light"
        inversestate = False
    elif robot.status == "idle":
        colorstate = "warning"
        inversestate = True
    else:
        colorstate = "danger"
        inversestate = True

    if robot.solution == "fix":
        colorsolution = "light"
        inversesolution = False
    elif robot.solution == "float":
        colorsolution = "warning"
        inversesolution = True
    else:
        colorsolution = "danger"
        inversesolution = True

    if robot.soc > 30:
        colorsoc = "light"
        inversesoc = False
    elif robot.soc > 15:
        colorsoc = "warning"
        inversesoc = True
    else:
        colorsoc = "danger"
        inversesoc = True


    return dbc.CardGroup(
        [
            dbc.Card(
                [
                    #dbc.CardHeader("Solution", className="truncate-1 stateCardHeader"),
                    dbc.CardBody(
                        [
                            html.Small(robot.solution.capitalize(), className="truncate-1"),
                            html.Small([
                                        '{}'.format(robot.position_visible_satellites_dgps)+'/{}'.format(robot.position_visible_satellites)+'('+robot.position_age_hr+')'
                                    ], style={'font-size': '0.63rem'}, className="truncate-1")
                        ],
                        class_name=CARD_BODY_CLASSES
                    ),
                ],
                className="text-center flex-grow-1",
                color=colorsolution,
                inverse=inversesolution,
                style=CARD_STYLES,
            ),
            dbc.Card(
                [
                    #dbc.CardHeader("State", className="truncate-1 stateCardHeader"),
                    dbc.CardBody(
                        [
                            html.Small(robot.status.capitalize(), className="truncate-1"),
                            html.Small(['{}'.format(robot.sensor_status)], style={'font-size': '0.63rem'}, className="truncate-1")
                        ],
                        class_name=CARD_BODY_CLASSES
                    ),
                ],
                className="text-center flex-grow-1",
                color=colorstate,
                inverse=inversestate,
                style=CARD_STYLES,
            ),
            dbc.Card(
                [
                    #dbc.CardHeader("SoC", className="truncate-1 stateCardHeader"),
                    dbc.CardBody(
                        [
                            html.Small("{}%".format(robot.soc).capitalize(), className="truncate-1"),
                            html.Small(['{}V'.format(round(robot.battery_voltage, 1))+' '+'{}A'.format(round(robot.amps, 1))], style={'font-size': '0.63rem'}, className="truncate-1")
                        ],
                        class_name=CARD_BODY_CLASSES
                    ),
                ],
                className="text-center flex-grow-1",
                color=colorsoc,
                inverse=inversesoc,
                style=CARD_STYLES,
            ),
        ],
        class_name="d-flex flex-justify-stretch",  # avoid wrapping on small screens
    )
