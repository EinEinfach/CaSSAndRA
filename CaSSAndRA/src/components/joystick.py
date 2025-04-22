from dash import html, Input, Output, callback, ctx
from dash_daq import Joystick
import math

from . import ids
from src.backend.comm import cmdlist
from src.backend.data.roverdata import robot
from src.backend.comm.robotinterface import robotInterface


@callback(Output(ids.LINEAR_SPEED, 'children'),
        Output(ids.ANGULAR_SPEED, 'children'),
        Input(ids.JOYSTICK, 'angle'),
        Input(ids.JOYSTICK, 'force'),
        Input(ids.JOYSTICKINTERVAL, 'n_intervals'),
        )
def update_output(angle, force, n_intervals):
    context = ctx.triggered_id
    force = min(0.5*force, 0.5)
    force_x = round(math.sin(math.radians(angle))*force, 2)
    force_y = -1*round(math.cos(math.radians(angle))*force, 2)
    if context == ids.JOYSTICK:
        robot.cmd_move_lin = force_x
        robot.cmd_move_ang = force_y
        # cmdlist.cmd_move = True
        robotInterface.performCmd('move')
    elif context == ids.JOYSTICKINTERVAL and (force_x != 0 or force_y != 0):
        robot.cmd_move_lin = force_x
        robot.cmd_move_ang = force_y
        robotInterface.performCmd('move')
    return f'{force_x}', f'{force_y}'
    
joystick = Joystick(id=ids.JOYSTICK, size=230, angle=0, force=0)
