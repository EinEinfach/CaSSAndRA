import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

from src.components import (
    ids,
    navbar,
    offcanvas,
    modalremotecontrol,
    modalinfo,
    modalerror,
)

from src.backend.data.mapdata import current_map


def serve_layout() -> html.Div:
    return html.Div(
        [
            dcc.Interval(id=ids.INTERVAL, interval=2*1000, n_intervals=0),
            dcc.Interval(id=ids.STATEMAPINTERVAL, interval=1*1000, n_intervals=0, disabled=False),
            dcc.Interval(id=ids.MAPPINGINTERVAL, interval=3*1000, n_intervals=0, disabled=True),
            dcc.Interval(id=ids.LOGINTERVAL, interval=3*1000, n_intervals=0, disabled=True),
            dcc.Location(id=ids.URLUPDATE, refresh=True),
            navbar.navbar,
            offcanvas.offcanvas,
            modalremotecontrol.confirm,
            modalinfo.info,
            modalerror.mapuploadfailed,
            dash.page_container
            # footer
        ]
    )

@callback([
            Output(ids.STATEPROGRESSBAR, 'value'),
            Output(ids.STATEPROGRESSBAR, 'class_name'),
            Output(ids.STATEPROGRESSBARCONTAINER, 'className'),
            ],
            [
                Input(ids.INTERVAL, 'n_intervals'),
            ])
def update_progress_bar(n_intervals: int
                        ) -> list:
    # Progress bar
    if current_map.total_progress > 0:
        progress = (current_map.calculated_progress / current_map.total_progress) * 100
    else:
        progress = 0

    if current_map.total_progress == 0:
        progress_class_name = "progress-bar-hidden"
        progress_container_class_name = "progress-bar-container-hidden"
    else:
        progress_class_name = "progress-bar-visible"
        progress_container_class_name = "progress-bar-container-visible"
    return progress, progress_class_name, progress_container_class_name
