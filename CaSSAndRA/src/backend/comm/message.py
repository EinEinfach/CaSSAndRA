import logging
logger = logging.getLogger(__name__)

import pandas as pd

from src.backend.data import mapdata
from src.backend.data.roverdata import robot
from src.backend.data.mapdata import current_map
from . import cmdtorover, cmdlist

def checkmowmotor(msg: pd.DataFrame, oldstate: bool) -> bool:
    mowmotorcmd = int(msg.iloc[-1]['msg'].split(',')[1])
    if mowmotorcmd == 1:
        return True
    elif mowmotorcmd == 0:
        return False
    else:
        return oldstate

def check() -> pd.DataFrame():

    if cmdlist.cmd_stop:
        msg_pckg = cmdtorover.stop()
        robot.last_mow_status = checkmowmotor(msg_pckg, robot.last_mow_status)
        cmdlist.cmd_stop = False

    elif cmdlist.cmd_move:
        msg_pckg = cmdtorover.move([robot.cmd_move_lin, robot.cmd_move_ang])  

    elif cmdlist.cmd_goto:
        map_msg = cmdtorover.takemap(current_map.perimeter, current_map.gotopoint, dock=False)
        goto_msg = cmdtorover.goto()
        msg_pckg = pd.concat([map_msg, goto_msg], ignore_index=True)
        robot.current_task = current_map.gotopoint
        robot.last_cmd = goto_msg
        robot.last_task_name = 'go to'
        robot.last_mow_status = checkmowmotor(goto_msg, robot.last_mow_status)
        cmdlist.cmd_goto = False

    elif cmdlist.cmd_dock:
        map_msg = cmdtorover.takemap(current_map.perimeter, pd.DataFrame(), dock=True)
        dock_msg = cmdtorover.dock()
        if robot.last_task_name == 'go to':
            msg_pckg = pd.concat([map_msg, dock_msg], ignore_index=True)
        else:
            msg_pckg = dock_msg
        #robot.last_cmd = dock_msg
        robot.last_mow_status = checkmowmotor(dock_msg, robot.last_mow_status)
        cmdlist.cmd_dock = False
    
    elif cmdlist.cmd_mow:
        map_msg = cmdtorover.takemap(current_map.perimeter, current_map.mowpath, dock=True)
        mow_msg = cmdtorover.mow()
        msg_pckg = pd.concat([map_msg, mow_msg], ignore_index=True)
        robot.current_task = current_map.mowpath
        robot.last_cmd = mow_msg
        robot.last_task_name = 'mow'
        robot.last_mow_status = checkmowmotor(mow_msg, robot.last_mow_status)
        cmdlist.cmd_mow = False
    
    elif cmdlist.cmd_resume:
        msg_pckg = robot.last_cmd
        robot.last_mow_status = checkmowmotor(msg_pckg, robot.last_mow_status)
        cmdlist.cmd_resume = False
    
    elif cmdlist.cmd_shutdown:
        msg_pckg = cmdtorover.shutdown()
        cmdlist.cmd_shutdown = False
    
    elif cmdlist.cmd_reboot:
        msg_pckg = cmdtorover.reboot()
        cmdlist.cmd_reboot = False
    
    elif cmdlist.cmd_gps_reboot:
        msg_pckg = cmdtorover.gpsreboot()
        cmdlist.cmd_gps_reboot = False
    
    elif cmdlist.cmd_toggle_mow_motor:
        msg_pckg = cmdtorover.togglemowmotor()
        robot.last_mow_status = checkmowmotor(msg_pckg, robot.last_mow_status)
        cmdlist.cmd_toggle_mow_motor = False
    
    elif cmdlist.cmd_set_positionmode:
        msg_pckg = cmdtorover.takepositionmode()
        cmdlist.cmd_set_positionmode = False
    
    elif cmdlist.cmd_changemowspeed:
        msg_pckg = cmdtorover.changespeed(robot.mowspeed_setpoint)
        robot.last_mow_status = checkmowmotor(msg_pckg, robot.last_mow_status)
        cmdlist.cmd_changemowspeed = False

    elif cmdlist.cmd_changegotospeed:
        msg_pckg = cmdtorover.changespeed(robot.gotospeed_setpoint)
        robot.last_mow_status = checkmowmotor(msg_pckg, robot.last_mow_status)
        cmdlist.cmd_changegotospeed = False
    
    elif cmdlist.cmd_skipnextpoint:
        msg_pckg = cmdtorover.skipnextpoint()
        robot.last_mow_status = checkmowmotor(msg_pckg, robot.last_mow_status)
        cmdlist.cmd_skipnextpoint = False

    else:
        msg_pckg = pd.DataFrame()

    return msg_pckg
