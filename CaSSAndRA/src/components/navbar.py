# package imports
from dash import html, callback, Output, Input, State
import dash_bootstrap_components as dbc

# local imports
from . import ids

# component
navbar = dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink('Home', href='/')),
            dbc.DropdownMenu(
                children=[
                    #dbc.DropdownMenuItem('More pages', header=True),
                    #dbc.DropdownMenuItem('Taskplanner', href='/taskplanner'),
                    #dbc.DropdownMenuItem('Statistik', href='/stats'),
                    dbc.DropdownMenuItem('Mapping', href='/mapping'),
                    dbc.DropdownMenuItem('Settings', href='/settings'),
                ],
                nav=True,
                in_navbar=True,
                label="More",
            ),
            dbc.Button(id=ids.OPEN_OFFCANVAS, n_clicks=0, size='lg',class_name='bi bi-joystick ms-3'),
            dbc.Button(id=ids.BUTTONOPENMODALINFO, n_clicks=0, size='lg',class_name='bi bi-info-square ms-3')
        ],
        brand="CaSSAndRA",
        brand_href="/",
        color="primary",
        dark=True,
    )
