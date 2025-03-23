# package imports
from dash import html, callback, Output, Input, State, ctx
import dash_bootstrap_components as dbc

# local imports
from . import ids
import os

mowername = os.getenv("MOWERNAME", "CaSSAndRA")  # Standard"CaSSAndRA"

# component
navbar = dbc.Navbar(
    [
        dbc.NavbarToggler(id=ids.NAVBARTOGGLER, n_clicks=0, class_name='mx-1 px-2'),
        dbc.NavbarBrand(
            [
                dbc.NavLink(mowername, id=ids.NAVBARSTATELINK, href='/', active='partial', n_clicks=0, class_name='mx-2 flex-grow-1'), 
            ],
        ),
        dbc.Nav(
            dbc.NavItem(
                [
                    dbc.Button(
                        id=ids.OPEN_OFFCANVAS,
                        n_clicks=0,
                        size='lg',
                        class_name='bi bi-joystick',
                        title='open remote control',
                    ),
                    dbc.Button(
                        id=ids.BUTTONOPENMODALINFO,
                        n_clicks=0,
                        size='lg',
                        class_name='bi bi-info-square',
                        title='open infobox',
                    ),
                ]
            ),
            className='order-md-2 flex-grow-1 align-items-end justify-content-end',
        ),
        dbc.Collapse(
            dbc.Nav(
                [
                    #dbc.NavItem(dbc.NavLink('State', href='/', active='exact')),
                    dbc.NavItem(
                        dbc.NavLink('Taskplanner', id=ids.NAVBARTASKSLINK, href='/taskplanner', active='partial', n_clicks=0)
                    ),
                    dbc.NavItem(
                        dbc.NavLink('Mapping', id=ids.NAVBARMAPLINK, href='/mapping', active='partial', n_clicks=0)
                    ),
                    dbc.NavItem(
                        dbc.NavLink('Settings', id=ids.NAVBARSETTINGSLINK, href='/settings', active='partial', n_clicks=0)
                    ),
                    dbc.NavItem(
                        dbc.NavLink('Log', id=ids.NAVBARLOGLINK, href='/log', active='partial', n_clicks=0)
                    ),
                    # dbc.NavItem(dbc.NavLink('Statistik', href='/stats')),
                ],
                class_name='mx-2',
            ),
            id=ids.NAVBARCOLLAPSE,
            is_open=False,
            navbar=True,
            class_name='order-md-1 px-2 flex-grow-5 justify-content-center',
        ),
    ],
    color='primary',
    dark=True,
    class_name='d-flex justify-content-start px-2',
    style={"padding-top":"0.25rem", "padding-bottom":"0.25rem"}
)


# add callback for toggling the collapse on small screens
@callback(
    Output(ids.NAVBARCOLLAPSE, 'is_open'),
    [Input(ids.NAVBARTOGGLER, 'n_clicks'),
     Input(ids.NAVBARSTATELINK, 'n_clicks'),
     Input(ids.NAVBARTASKSLINK, 'n_clicks'),
     Input(ids.NAVBARMAPLINK, 'n_clicks'),
     Input(ids.NAVBARSETTINGSLINK, 'n_clicks'),
     Input(ids.NAVBARLOGLINK, 'n_clicks'),
    ],
    [State(ids.NAVBARCOLLAPSE, 'is_open')],
)
def toggle_navbar_collapse(toggler, state, tasks, map, settings, log, is_open):
    button_clicked = ctx.triggered_id
    if button_clicked == ids.NAVBARTOGGLER:
        return not is_open
    return False

