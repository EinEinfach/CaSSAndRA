from dash import html, Input, Output, callback, ctx
from dash_daq import Joystick
import math

from . import ids
from src.backend.comm import cmdlist
from src.backend.data.roverdata import robot


@callback(Output(ids.LINEAR_SPEED, 'children'),
        Output(ids.ANGULAR_SPEED, 'children'),
        Input(ids.JOYSTICK, 'angle'),
        Input(ids.JOYSTICK, 'force')
        )
def update_output(angle, force):
    context = ctx.triggered_id
    force = min(0.5*force, 0.5)
    force_x = round(math.sin(math.radians(angle))*force, 2)
    force_y = -1*round(math.cos(math.radians(angle))*force, 2)
    if context == ids.JOYSTICK:
        cmdlist.cmd_move = True
        robot.cmd_move_lin = force_x
        robot.cmd_move_ang = force_y
    return f'{force_x}', f'{force_y}'
    
joystick = Joystick(id=ids.JOYSTICK, size=230, angle=0, force=0)
