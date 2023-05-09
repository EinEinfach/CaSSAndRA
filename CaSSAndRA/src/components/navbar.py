# package imports
from dash import html, callback, Output, Input, State
import dash_bootstrap_components as dbc

# local imports
from . import ids

# component
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.NavbarBrand("CaSSAndRA",href="/"),
            dbc.Nav(dbc.NavItem([
                dbc.Button(id=ids.OPEN_OFFCANVAS, n_clicks=0, size='lg',class_name='bi bi-joystick', title='Open Remote Control'),
                dbc.Button(id=ids.BUTTONOPENMODALINFO, n_clicks=0, size='lg',class_name='bi bi-info-square ms-3 me-5', title='Open Infobox')
            ]), className="ms-auto"),

            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink('Mapping', href='/mapping')),
                    dbc.NavItem(dbc.NavLink('Settings', href='/settings')),
                    #dbc.NavItem(dbc.NavLink('Taskplanner', href='/taskplanner')),
                    #dbc.NavItem(dbc.NavLink('Statistik', href='/stats')),
                ]),
            id="navbar-collapse",
            is_open=False,
            navbar=True,
            ),
        ]),
    className="mb-2",
    color="primary",
    dark=True,
)

# add callback for toggling the collapse on small screens
@callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return False