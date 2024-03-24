import logging
logger = logging.getLogger(__name__)

import pandas as pd
from datetime import datetime

from src.backend.data.mapdata import current_map
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

def check() -> pd.DataFrame:

    msg_pckg = pd.DataFrame()

    if cmdlist.cmd_stop:
        msg_pckg = cmdtorover.stop()
        robot.last_mow_status = checkmowmotor(msg_pckg, robot.last_mow_status)
        cmdlist.cmd_stop = False

    elif cmdlist.cmd_move:
        msg_pckg = cmdtorover.move([robot.cmd_move_lin, robot.cmd_move_ang])  

    elif cmdlist.cmd_goto:
        if cmdlist.cmd_take_map_attempt == 0 or robot.map_upload_failed:
            if cmdlist.cmd_take_map_attempt == 0:
                robot.map_old_crc = robot.map_crc
            robot.map_upload_started = True 
            robot.map_upload_finished = False
            robot.map_upload_failed = False
            perimeter_no_dockpath = current_map.perimeter[(current_map.perimeter['type'] != 'dockpoints') & (current_map.perimeter['type'] != 'search wire')]
            data = pd.concat([perimeter_no_dockpath, current_map.gotopoint], ignore_index=True)
            mapCRCx = data['X']*100 
            mapCRCy = data['Y']*100
            current_map.map_crc = int(mapCRCx.sum() + mapCRCy.sum())
            if cmdlist.cmd_take_map_attempt >= 5:
                logger.warning('Backend: Could not upload map to the rover')
                cmdlist.cmd_take_map_attempt = 0
                cmdlist.cmd_failed = True
                cmdlist.cmd_goto = False
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = False
                return pd.DataFrame()
            logger.debug('Map crc deivation: '+str(abs(current_map.map_crc - robot.map_crc)))    
            logger.debug('Initiate map upload.')
            cmdlist.cmd_take_map_attempt = cmdlist.cmd_take_map_attempt + 1
            map_msg = cmdtorover.takemap(current_map.perimeter, current_map.gotopoint, dock=False)
            msg_pckg = map_msg
            return msg_pckg
         
        if robot.map_upload_finished:
            map_crc_dev = abs(current_map.map_crc - robot.map_crc)
            if map_crc_dev < 100:
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = False
                logger.debug('Current map crc matches rover map crc, perform goto command. CRC deviation: '+str(map_crc_dev))
                cmdlist.cmd_take_map_attempt = 0
                goto_msg = cmdtorover.goto()
                msg_pckg = goto_msg
                robot.current_task = current_map.gotopoint
                robot.last_cmd = goto_msg
                robot.last_task_name = 'go to'
                robot.last_mow_status = checkmowmotor(goto_msg, robot.last_mow_status)
                cmdlist.cmd_goto = False
                return msg_pckg
            else:
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = True
                return pd.DataFrame() 
        else:
            return pd.DataFrame()    
   
    elif cmdlist.cmd_dock:
        if robot.last_task_name == 'go to':
            if cmdlist.cmd_take_map_attempt == 0 or robot.map_upload_failed:
                if cmdlist.cmd_take_map_attempt == 0:
                    robot.map_old_crc = robot.map_crc
                robot.map_upload_started = True 
                robot.map_upload_finished = False
                robot.map_upload_failed = False
                data = current_map.perimeter[current_map.perimeter['type'] != 'search wire'] 
                mapCRCx = data['X']*100 
                mapCRCy = data['Y']*100
                current_map.map_crc = int(mapCRCx.sum() + mapCRCy.sum())
                if cmdlist.cmd_take_map_attempt >= 5:
                    logger.warning('Backend: Could not upload map to the rover')
                    cmdlist.cmd_take_map_attempt = 0
                    cmdlist.cmd_failed = True
                    cmdlist.cmd_dock = False
                    robot.map_upload_started = False
                    robot.map_upload_finished = False
                    robot.map_upload_failed = False
                    return pd.DataFrame()
                logger.debug('Map crc deivation: '+str(abs(current_map.map_crc - robot.map_crc)))    
                logger.debug('Initiate map upload.')
                cmdlist.cmd_take_map_attempt = cmdlist.cmd_take_map_attempt + 1
                map_msg = cmdtorover.takemap(current_map.perimeter, pd.DataFrame(), dock=True)
                msg_pckg = map_msg
                return msg_pckg
                
            if robot.map_upload_finished:
                map_crc_dev = abs(current_map.map_crc - robot.map_crc)
                if map_crc_dev < 100:
                    robot.map_upload_started = False
                    robot.map_upload_finished = False
                    robot.map_upload_failed = False
                    logger.debug('Current map crc matches rover map crc, perfom dock command. CRC deviation: '+str(map_crc_dev))
                    cmdlist.cmd_take_map_attempt = 0
                    dock_msg= cmdtorover.dock()
                    msg_pckg = dock_msg
                    robot.last_mow_status = checkmowmotor(dock_msg, robot.last_mow_status)
                    cmdlist.cmd_dock = False
                    robot.dock_reason_operator = True
                    robot.dock_reason = 'operator'
                    robot.dock_reason_time = datetime.now()
                    return msg_pckg 
                else:
                    robot.map_upload_started = False
                    robot.map_upload_finished = False
                    robot.map_upload_failed = True
                    return pd.DataFrame() 
        else:
            dock_msg = cmdtorover.dock()   
            msg_pckg = dock_msg
            robot.last_mow_status = checkmowmotor(dock_msg, robot.last_mow_status)
            cmdlist.cmd_dock = False
            robot.dock_reason_operator = True
            robot.dock_reason = 'operator'
            robot.dock_reason_time = datetime.now()
            return msg_pckg
    
    elif cmdlist.cmd_dock_schedule:
        dock_msg = cmdtorover.dock()   
        msg_pckg = dock_msg
        robot.last_mow_status = checkmowmotor(dock_msg, robot.last_mow_status)
        cmdlist.cmd_dock_schedule = False
        robot.dock_reason_operator = True
        robot.dock_reason = 'schedule'
        robot.dock_reason_time = datetime.now()
        return msg_pckg
    
    elif cmdlist.cmd_mow:
        if cmdlist.cmd_take_map_attempt == 0 or robot.map_upload_failed:
            if cmdlist.cmd_take_map_attempt == 0:
                robot.map_old_crc = robot.map_crc
            robot.map_upload_started = True 
            robot.map_upload_finished = False
            robot.map_upload_failed = False
            data = current_map.perimeter[current_map.perimeter['type'] != 'search wire']
            data = pd.concat([data, current_map.mowpath], ignore_index=True)
            mapCRCx = data['X']*100 
            mapCRCy = data['Y']*100
            current_map.map_crc = int(mapCRCx.sum() + mapCRCy.sum())
            if cmdlist.cmd_take_map_attempt >= 5:
                logger.warning('Backend: Could not upload map to the rover')
                cmdlist.cmd_take_map_attempt = 0
                cmdlist.cmd_failed = True
                cmdlist.cmd_mow = False
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = False
                return pd.DataFrame()
            logger.debug('Map crc deivation: '+str(abs(current_map.map_crc - robot.map_crc)))    
            logger.debug('Initiate map upload.')
            cmdlist.cmd_take_map_attempt = cmdlist.cmd_take_map_attempt + 1
            map_msg = cmdtorover.takemap(current_map.perimeter, current_map.mowpath, dock=True)
            msg_pckg = map_msg
            return msg_pckg
            
        if robot.map_upload_finished:
            map_crc_dev = abs(current_map.map_crc - robot.map_crc)
            if map_crc_dev < 500:
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = False
                logger.debug('Current map crc matches rover map crc, perform mow command. CRC deviation: '+str(map_crc_dev))
                cmdlist.cmd_take_map_attempt = 0
                mow_msg = cmdtorover.mow()
                msg_pckg = mow_msg
                robot.current_task = current_map.mowpath
                robot.last_cmd = mow_msg
                robot.last_task_name = 'mow'
                robot.last_mow_status = checkmowmotor(mow_msg, robot.last_mow_status)
                cmdlist.cmd_mow = False
                return msg_pckg
            else:
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = True
                return pd.DataFrame() 
        else:
            return pd.DataFrame()    

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
    
    elif cmdlist.cmd_take_map:
        if cmdlist.cmd_take_map_attempt == 0 or robot.map_upload_failed:
            if cmdlist.cmd_take_map_attempt == 0:
                robot.map_old_crc = robot.map_crc
            robot.map_upload_started = True 
            robot.map_upload_finished = False
            robot.map_upload_failed = False
            data = current_map.perimeter[current_map.perimeter['type'] != 'search wire']
            data = pd.concat([data, current_map.mowpath], ignore_index=True)
            mapCRCx = data['X']*100 
            mapCRCy = data['Y']*100
            current_map.map_crc = int(mapCRCx.sum() + mapCRCy.sum())
            if cmdlist.cmd_take_map_attempt >= 5:
                logger.warning('Backend: Could not upload map to the rover')
                cmdlist.cmd_take_map_attempt = 0
                cmdlist.cmd_failed = True
                cmdlist.cmd_take_map = False
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = False
                return pd.DataFrame()
            logger.debug('Map crc deivation: '+str(abs(current_map.map_crc - robot.map_crc)))    
            logger.debug('Initiate map upload.')
            cmdlist.cmd_take_map_attempt = cmdlist.cmd_take_map_attempt + 1
            map_msg = cmdtorover.takemap(current_map.perimeter, current_map.mowpath, dock=True)
            msg_pckg = map_msg
            return msg_pckg
            
        if robot.map_upload_finished:
            map_crc_dev = abs(current_map.map_crc - robot.map_crc)
            if map_crc_dev < 500:
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = False
                logger.debug('Current map crc matches rover map crc, stand by. CRC deviation: '+str(map_crc_dev))
                cmdlist.cmd_take_map_attempt = 0
                mow_msg = cmdtorover.mow()
                msg_pckg = mow_msg
                robot.current_task = current_map.mowpath
                robot.last_cmd = mow_msg
                cmdlist.cmd_take_map = False
                return pd.DataFrame()
            else:
                robot.map_upload_started = False
                robot.map_upload_finished = False
                robot.map_upload_failed = True
                return pd.DataFrame() 
        else:
            return pd.DataFrame()  
    
    elif cmdlist.cmd_skiptomowprogress:
        msg_pckg = cmdtorover.skiptomowprogress(robot.mowprogress)
        cmdlist.cmd_skiptomowprogress = False 

    elif cmdlist.cmd_custom:
        msg_pckg = cmdtorover.custom()
        cmdlist.cmd_custom = False

    return msg_pckg
