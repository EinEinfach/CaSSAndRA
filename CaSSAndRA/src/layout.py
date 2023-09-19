import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.components import (
    ids,
    navbar,
    offcanvas,
    modalremotecontrol,
    modalinfo,
    modalerror,
)


def serve_layout() -> html.Div:
    return html.Div(
        [
            dcc.Interval(id=ids.INTERVAL, interval=1 * 3000, n_intervals=0),
            dcc.Interval(
                id=ids.STATEMAPINTERVAL,
                interval=1 * 1000,
                n_intervals=0,
                disabled=False,
            ),
            dcc.Interval(
                id=ids.MAPPINGINTERVAL, interval=1 * 3000, n_intervals=0, disabled=True
            ),
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
