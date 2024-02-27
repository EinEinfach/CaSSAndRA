#package imports
from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

#locale imports
from . import joystick, ids
from ..backend.data.roverdata import robot
from ..backend.data.cfgdata import rovercfg
from ..backend.comm import cmdlist

offcanvas =dbc.Offcanvas([
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader('linear speed'),
                            dbc.CardBody(html.H6(id=ids.LINEAR_SPEED))
                        ], className='text-center mb-2')
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader('angular speed'),
                            dbc.CardBody(html.H6(id=ids.ANGULAR_SPEED))
                        ], className='text-center mb-2')
                    )
                ]),
                dbc.Row(
                    dbc.Col([
                        joystick.joystick
                    ])
                ),
                dbc.Row(
                    dbc.Col([
                       dbc.Card([
                           dbc.CardBody(id=ids.SPEEDSETPOINTOFFCANVAS),
                       ], class_name='text-center mb-2 mt-2')
                    ])
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(id=ids.BUTTONSLOWER, 
                                   size='lg', 
                                   class_name='mx-1 bi bi-dash-square', 
                                   title='slower')
                                   ], 
                                class_name='d-grid col-md4'
                        ),
                    dbc.Col([
                        dbc.Button(id=ids.BUTTONFASTER, 
                                   size='lg', 
                                   class_name='mx-1 bi bi-plus-square', 
                                   title='faster')
                                   ], 
                                class_name='d-grid col-md4'
                        ),
                ]),
                dbc.Row([
                    dbc.Col(),
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONFAN, 
                                   class_name='bi bi-fan mt-2', 
                                   color='info', 
                                   size='lg',
                                   title='start/stop blade motor'
                        ), class_name='text-center'
                    ),
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONNEXTPOINT, 
                                   class_name='bi bi-skip-end mt-2',  
                                   size='lg',
                                   title='skip next point'
                        ), class_name='text-center'
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONSUNRAYOFF, 
                                   class_name='bi bi-lightbulb-off mt-2', 
                                   color='danger', 
                                   size='lg',
                                   title='shutdown'
                        ), class_name='text-center'
                    ),
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONSUNRAYREBOOT, 
                                   class_name='bi bi-bootstrap-reboot mt-2', 
                                   color='warning', 
                                   size='lg',
                                   title='reboot sunray fw and backend server'
                        ), class_name='text-center'
                    ),
                    dbc.Col(
                        dbc.Button(id=ids.BUTTONGPSREBOOT, 
                                   class_name='bi bi-stars mt-2', 
                                   color='info', 
                                   size='lg',
                                   title='reboot gps'
                        ), class_name='text-center'
                    ),
                    #html.Div(id='offcanvas-hidden')
                ])
                ],
                placement='end',
                style={'width': 260},
                id=ids.OFFCANVAS,
                title="Remote control",
                is_open=False,
            )              

@callback(Output(ids.OFFCANVAS, "is_open"),
        Input(ids.OPEN_OFFCANVAS, "n_clicks"),
        [State(ids.OFFCANVAS, "is_open")],)
def toggle_offcanvas(n_clicks: int, is_open: bool) -> bool:
    if n_clicks:
        return not is_open
    return is_open

@callback(Output(ids.BUTTONSLOWER, 'active'),
          Output(ids.BUTTONFASTER, 'active'),
          [Input(ids.BUTTONSLOWER, 'n_clicks'),
           Input(ids.BUTTONFASTER, 'n_clicks')])
def update_speed_setpoint(bs_nclicks, bf_nclicks) -> str:
    context = ctx.triggered_id
    if context == ids.BUTTONSLOWER and robot.status == 'mow':
        robot.change_speed('mow', -0.01)
        cmdlist.cmd_changemowspeed = True
    elif context == ids.BUTTONSLOWER and robot.status == 'transit':
        robot.change_speed('goto', -0.01)
        cmdlist.cmd_changegotospeed = True
    elif context == ids.BUTTONFASTER and robot.status == 'mow':
        robot.change_speed('mow', 0.01)
        cmdlist.cmd_changemowspeed = True
    elif context == ids.BUTTONFASTER and robot.status == 'transit':
        robot.change_speed('goto', 0.01)
        cmdlist.cmd_changegotospeed = True
    
    return False, False

@callback(Output(ids.SPEEDSETPOINTOFFCANVAS, 'children'),
          [Input(ids.BUTTONSLOWER, 'active'),
           Input(ids.BUTTONFASTER, 'active'),
           Input(ids.INTERVAL, 'n_intervals')])
def update_display_speed_setpoint(bs_active: bool, bf_active: bool, nintervals: int) -> str:
    context = ctx.triggered_id
    if robot.status == 'transit':
        return 'transit speed: '+str(robot.gotospeed_setpoint)
    elif robot.status == 'mow':
        return 'mow speed: '+str(robot.mowspeed_setpoint)
    else:
        return '---'

@callback(Output(ids.BUTTONNEXTPOINT, 'active'),
          [Input(ids.BUTTONNEXTPOINT, 'n_clicks')])
def update_next_point(bnp_nclicks: int) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONNEXTPOINT:
        cmdlist.cmd_stop = True
        time.sleep(1)
        cmdlist.cmd_skipnextpoint = True
        time.sleep(0.5)
        cmdlist.cmd_resume = True
    return False


    