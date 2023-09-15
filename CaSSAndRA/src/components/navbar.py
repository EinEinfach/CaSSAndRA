# package imports
from dash import html, callback, Output, Input, State
import dash_bootstrap_components as dbc

# local imports
from . import ids

# component
navbar = dbc.Navbar(
    [
        dbc.NavbarToggler(id=ids.NAVBARTOGGLER, n_clicks=0, class_name='mx-1 px-2'),
        dbc.NavbarBrand('CaSSAndRA', href='/', class_name='mx-2 flex-grow-1'),
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
                        dbc.NavLink(
                            'Taskplanner', href='/taskplanner', active='partial'
                        )
                    ),
                    dbc.NavItem(
                        dbc.NavLink('Mapping', href='/mapping', active='partial')
                    ),
                    dbc.NavItem(
                        dbc.NavLink('Settings', href='/settings', active='partial')
                    ),
                    dbc.NavItem(
                        dbc.NavLink('Log', href='/log', active='partial')
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
)


# add callback for toggling the collapse on small screens
@callback(
    Output(ids.NAVBARCOLLAPSE, 'is_open'),
    [Input(ids.NAVBARTOGGLER, 'n_clicks')],
    [State(ids.NAVBARCOLLAPSE, 'is_open')],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return False
