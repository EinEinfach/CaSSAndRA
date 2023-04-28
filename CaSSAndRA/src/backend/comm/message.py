import logging
logger = logging.getLogger(__name__)

import pandas as pd

from src.backend.data import roverdata, mapdata
from . import cmdtorover, cmdlist

def check() -> pd.DataFrame():

    if cmdlist.cmd_stop:
        msg_pckg = cmdtorover.stop()
        cmdlist.cmd_stop = False

    elif cmdlist.cmd_move:
        msg_pckg = cmdtorover.move(roverdata.cmd_move)  

    elif cmdlist.cmd_goto:
        map_msg = cmdtorover.takemap(mapdata.perimeter, mapdata.gotopoint, dock=False)
        goto_msg = cmdtorover.goto()
        msg_pckg = pd.concat([map_msg, goto_msg], ignore_index=True)
        roverdata.current_task = mapdata.gotopoint
        roverdata.last_cmd = goto_msg
        cmdlist.cmd_goto = False

    elif cmdlist.cmd_dock:
         map_msg = cmdtorover.takemap(mapdata.perimeter, pd.DataFrame(), dock=True)
         dock_msg = cmdtorover.dock()
         msg_pckg = pd.concat([map_msg, dock_msg], ignore_index=True)
         roverdata.last_cmd = dock_msg
         cmdlist.cmd_dock = False
    
    elif cmdlist.cmd_mow:
        map_msg = cmdtorover.takemap(mapdata.perimeter, mapdata.mowpath, dock=True)
        mow_msg = cmdtorover.mow()
        msg_pckg = pd.concat([map_msg, mow_msg], ignore_index=True)
        roverdata.current_task = mapdata.mowpath
        roverdata.last_cmd = mow_msg
        cmdlist.cmd_mow = False
    
    elif cmdlist.cmd_resume:
        msg_pckg = roverdata.last_cmd
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
        cmdlist.cmd_toggle_mow_motor = False
    
    elif cmdlist.cmd_set_positionmode:
        msg_pckg = cmdtorover.takepositionmode()
        cmdlist.cmd_set_positionmode = False

    else:
        msg_pckg = pd.DataFrame()

    return msg_pckg
