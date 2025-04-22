import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd

from ..data.mapdata import current_map
from ..data.roverdata import robot
from ..data import roverdata, calceddata
from . import sunraycommstack
from ..data import appdata
from ..data.cfgdata import appcfg

from icecream import ic

NEW_GOTO_APPROACH = True

@dataclass
class RobotInterface:
    activeCmd: str = None
    pendingRequest: str = None
    pendingRequestCnt: int = 0
    mapDataInBuffer: bool = False
    robotCmds: list = field(default_factory=lambda: list())
    cmdFailed: bool = False
    lastLoadWithDockPath: bool = False
    lastLinSpeed: float = 0.0
    lastAngSpeed: float = 0.0

    def _cmdTransmissionFailed(self) -> None:
        self.cmdFailed = True
        appdata.cmdTransmissionFailed = True

    def _checkPendingRequest(self) -> None:
        if self.pendingRequest == None:
            self.pendingRequestCnt = 0
            self.cmdFailed = False
            return
        if not self.mapDataInBuffer:
            if self.pendingRequest == 'goTo':
                self._cmdGoTo()
            elif self.pendingRequest == 'dock':
                self._cmdDock()
            elif self.pendingRequest == 'mow':
                self._cmdMow()
            elif self.pendingRequest == 'sendMap':
                self._cmdSendMap()

    def _checkMowMotorState(self, msg: pd.DataFrame, oldstate: bool) -> bool:
        mowmotorcmd = int(msg.iloc[-1]['msg'].split(',')[1])
        if mowmotorcmd == 1:
            return True
        elif mowmotorcmd == 0:
            return False
        else:
            return oldstate
    
    def _calcMapCrc(self, way: pd.DataFrame, dockpath: bool) -> None:
        dataForCrc = current_map.perimeter[current_map.perimeter['type'] != 'search wire']
        if not dockpath:
            dataForCrc = dataForCrc[dataForCrc['type'] != 'dockpoints']
        dataForCrc = pd.concat([dataForCrc, way], ignore_index=True)
        mapCRCx = dataForCrc['X']*100 
        mapCRCy = dataForCrc['Y']*100
        current_map.map_crc = int(mapCRCx.sum() + mapCRCy.sum())
        logger.debug('Map crc deivation: '+str(abs(current_map.map_crc - robot.map_crc)))
    
    def _onPropsMessage(self, props_df: pd.DataFrame) -> None:
        if not props_df.empty:
            robot.set_props(props_df)
            roverdata.props = pd.concat([roverdata.props, props_df], ignore_index=True)
    
    def _onStateMessage(self, state_df: pd.DataFrame) -> None:
        if not state_df.empty:
            robot.set_state(state_df)
            roverdata.state = pd.concat([roverdata.state, state_df], ignore_index=True)
            calceddata.calcdata_from_state()
            self._checkPendingRequest()
            return
        logger.warning('State data frame is empty')
    
    def _onStatsMessage(self, stats_df: pd.DataFrame) -> None:
        if not stats_df.empty:
            roverdata.stats = pd.concat([roverdata.stats, stats_df], ignore_index=True)
            calceddata.calcdata_from_stats() 
    
    def _onObstacleMessage(self, obstacles_df: pd.DataFrame) -> None:
        obstacles = current_map.obstacles
        if obstacles_df.empty:
           pass 
        elif not obstacles.empty:
            for obstacle in obstacles_df['CRC'].unique():
                if obstacles[obstacles['CRC'] == obstacle].empty:
                    obstacles = pd.concat([obstacles, obstacles_df[obstacles_df['CRC'] == obstacle]], ignore_index=True)
        else:
            obstacles = obstacles_df
        
        obstacles = self._cleanObstacles(obstacles_df, obstacles)

        if not obstacles.equals(current_map.obstacles):
            current_map.add_obstacles(obstacles)
            
    def _cleanObstacles(self, obstacles_df: pd.DataFrame, obstacles: pd.DataFrame) -> pd.DataFrame:
        if appcfg.obstacles_amount != 0 and not obstacles.empty:
                if len(obstacles['CRC'].unique()) > appcfg.obstacles_amount:
                    obstacles_crc = obstacles['CRC'].unique()
                    obstacles_crc = obstacles_crc[-appcfg.obstacles_amount:]
                    obstacles = obstacles[obstacles['CRC'].isin(obstacles_crc)]
                    obstacles = obstacles.reset_index(drop=True)

        elif appcfg.obstacles_amount == 0 and obstacles_df.empty: #Synchronize to sunray fw
            obstacles = pd.DataFrame()
        
        return obstacles

        
        
    def onRobotMessageReceived(self, type: str, message) -> None:
        if type == 'props':
            props_df = sunraycommstack.onpropsmessage(message)
            self._onPropsMessage(props_df)
        elif type == 'propsMqtt':
            props_df = sunraycommstack.onpropsmqttmessage(message)
            self._onPropsMessage(props_df)
        elif type == 'state':
            state_df = sunraycommstack.onstatemessage(message)
            self._onStateMessage(state_df)
        elif type == 'stateMqtt':
            state_df = sunraycommstack.onstatemqttmessage(message)
            self._onStateMessage(state_df)
        elif type == 'stats':
            stats_df = sunraycommstack.onstatsmessage(message)
            self._onStatsMessage(stats_df)
        elif type == 'statsMqtt':
            stats_df = sunraycommstack.onstatsmqttmessage(message)
            self._onStatsMessage(stats_df)
        elif type == 'obstacles':
            obstacles_df = sunraycommstack.onobstaclemessage(message)
            self._onObstacleMessage(obstacles_df)
        else:
            logger.warning('Unknown message type')
    
    def performCmd(self, cmd: str) -> None:
        self.activeCmd = cmd
        if cmd == 'stop':
            self._cmdStop()
        elif cmd == 'move':
            self._cmdMove()
        elif cmd == 'goTo':
            self._cmdGoTo()
        elif cmd == 'dock':
            self._cmdDock()
        elif cmd == 'dockSchedule':
            self._cmdDockSchedule()
        elif cmd == 'mow':
            self._cmdMow()
        elif cmd == 'sendMap':
            self._cmdSendMap()
        elif cmd == 'reboot':
            self._cmdReboot()
        elif cmd == 'shutdown':
            self._cmdShutdown()
        elif cmd == 'rebootGps':
            self._cmdGpsReboot()
        elif cmd == 'changeMowSpeed':
            self._cmdChangeMowspeed()
        elif cmd == 'changeGoToSpeed':
            self._cmdChangeGotoSpeed()
        elif cmd == 'skipNextPoint':
            self._cmdSkipNextPoint()
        elif cmd == 'skipToMowProgress':
            self._cmdSkipToMowProgress()
        elif cmd == 'setPositionMode':
            self._cmdSetPositionMode()
        elif cmd == 'toggleMowMotor':
            self._cmdToggleMowMowtor()
        elif cmd == 'resume':
            self._cmdResume()
        elif cmd == 'custom':
            self._cmdCustom()
        else:
            logger.warning('Server instance got unknown command')
    
    def resetRobotCmds(self) -> None:
        if self.robotCmds != []:
            del self.robotCmds[0]
        else:
            self.activeCmd = None
    
    def setRobotCmds(self, data: pd.DataFrame) -> None:
        self.robotCmds.append(data)
    
    def setForceRobotCmds(self, data: pd.DataFrame) -> None:
        self.robotCmds = []
        self.robotCmds.append(data)
    
    def getRobotCmds(self) -> pd.DataFrame:
        if self.robotCmds != []:
            return self.robotCmds[0]
        else:
            return pd.DataFrame()

    def _cmdStop(self) -> None:
        self.status = 'stop'
        logger.info(f'Send command to robot: {self.status}')
        robot.dock_reason = None
        cmd = sunraycommstack.stop()
        self.setRobotCmds(cmd)
        robot.last_mow_cmd= self._checkMowMotorState(cmd, robot.last_mow_cmd)
        robot.last_mow_status = robot.last_mow_cmd
    
    def _cmdMove(self) -> None:
        self.status = 'move'
        robot.dock_reason = None
        if robot.cmd_move_lin == 0 and robot.cmd_move_ang == 0:
            logger.info(f'Send command to robot: linear speed: {robot.cmd_move_lin}, angular speed: {robot.cmd_move_ang}')
            self.setForceRobotCmds(pd.DataFrame())
            self.lastLinSpeed = 0.0
            self.lastAngSpeed = 0.0
        else:
            robot.status_tmp_timestamp = datetime.now()
            robot.set_robot_status('move', 'move')
            if self.lastLinSpeed != robot.cmd_move_lin or self.lastAngSpeed != robot.cmd_move_ang:
                logger.info(f'Send command to robot: linear speed: {robot.cmd_move_lin}, angular speed: {robot.cmd_move_ang}')
                self.setForceRobotCmds(sunraycommstack.move([robot.cmd_move_lin, robot.cmd_move_ang]) )
                self.lastLinSpeed = robot.cmd_move_lin
                self.lastAngSpeed = robot.cmd_move_ang
            elif self.robotCmds == []:   
                logger.info(f'Send command to robot: linear speed: {robot.cmd_move_lin}, angular speed: {robot.cmd_move_ang}')
                self.setRobotCmds(sunraycommstack.move([robot.cmd_move_lin, robot.cmd_move_ang]) )
                self.lastLinSpeed = robot.cmd_move_lin
                self.lastAngSpeed = robot.cmd_move_ang
    
    def _cmdTakeMap(self, way: pd.DataFrame, dockpath: bool) -> None:
        self._calcMapCrc(way, dockpath)
        robot.status_timestamp = datetime.now()
        robot.set_robot_status('map upload', 'map upload')
        self.setRobotCmds(sunraycommstack.takemap(current_map.perimeter, way, dockpath))
        self.mapDataInBuffer = True
    
    def _cmdGoTo(self) -> None:
        self.pendingRequest = 'goTo'
        logger.info(f'Send command to robot: {self.pendingRequest}')
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif (abs(robot.map_crc - current_map.map_crc) < 200) and self.pendingRequestCnt > 1:
            robot.status_tmp_timestamp = datetime.now()
            robot.set_robot_status('transit', 'transit')
            robot.dock_reason = None
            cmd = sunraycommstack.goto()
            self.setRobotCmds(cmd)
            robot.last_cmd = cmd
            robot.last_mow_cmd = self._checkMowMotorState(robot.last_cmd, robot.last_mow_cmd)
            robot.last_mow_status = robot.last_mow_cmd
            robot.current_task = current_map.gotopoint
            self.lastLoadWithDockPath = False
            self.pendingRequest = None
            return
        else:
            logger.info(f'Current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.gotopoint, dockpath=NEW_GOTO_APPROACH)
    
    def _cmdDock(self) -> None:
        self.pendingRequest = 'dock'
        logger.info(f'Send command to robot: {self.pendingRequest}')
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif self.lastLoadWithDockPath or ((abs(robot.map_crc - current_map.map_crc) < 200) and self.pendingRequestCnt > 1):
            robot.status_tmp_timestamp = datetime.now()
            robot.set_robot_status('docking', 'docking')
            cmd = sunraycommstack.dock()
            self.setRobotCmds(cmd)
            robot.last_mow_cmd = self._checkMowMotorState(cmd, robot.last_mow_cmd)
            robot.last_mow_status = robot.last_mow_cmd
            robot.dock_reason = 'operator'
            robot.dock_reason_time = datetime.now()
            self.lastLoadWithDockPath = True
            self.pendingRequest = None
            return
        else:
            logger.info(f'Current map does not contain dock path or crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.gotopoint, dockpath=True)
    
    def _cmdDockSchedule(self) -> None:
        logger.info(f'Send command to robot: dockSchedule')
        robot.status_tmp_timestamp = datetime.now()
        robot.set_robot_status('docking', 'docking')
        robot.dock_reason = 'schedule'
        robot.dock_reason_time = datetime.now()
        cmd = sunraycommstack.dock()
        self.setRobotCmds(cmd)
        robot.last_mow_cmd = self._checkMowMotorState(cmd, robot.last_mow_cmd)
        robot.last_mow_status = robot.last_mow_cmd
        
    
    def _cmdMow(self) -> None:
        self.pendingRequest = 'mow'
        logger.info(f'Send command to robot: {self.pendingRequest}')
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif (abs(robot.map_crc - current_map.map_crc) < 200) and self.pendingRequestCnt > 1:
            robot.status_tmp_timestamp = datetime.now()
            robot.set_robot_status('mow', 'mow')
            robot.dock_reason = None
            cmd = sunraycommstack.mow()
            self.setRobotCmds(cmd)
            robot.last_cmd = cmd
            robot.last_mow_cmd = self._checkMowMotorState(robot.last_cmd, robot.last_mow_cmd)
            robot.last_mow_status = robot.last_mow_cmd
            robot.current_task = current_map.mowpath
            self.lastLoadWithDockPath = True
            self.pendingRequest = None
            return
        else:
            logger.info(f'Current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.mowpath, dockpath=True)
    
    def _cmdSendMap(self) -> None:
        self.pendingRequest = 'sendMap'
        logger.info(f'Send command to robot: {self.pendingRequest}')
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif (abs(robot.map_crc - current_map.map_crc < 100)) and self.pendingRequestCnt > 1:
            cmd = sunraycommstack.mow()
            # self.setRobotCmds(cmd)
            robot.last_cmd = cmd
            robot.last_mow_cmd = self._checkMowMotorState(robot.last_cmd, robot.last_mow_cmd)
            robot.current_task = current_map.mowpath
            self.lastLoadWithDockPath = True
            self.pendingRequest = None
        else:
            logger.info(f'Current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.mowpath, dockpath=True)
                         

    def _cmdResume(self) -> None:
        logger.info(f'Send command to robot: resume')
        robot.status_tmp_timestamp = datetime.now()
        robot.set_robot_status('resume', 'resume')
        robot.dock_reason = None
        cmd = sunraycommstack.resume()
        self.setRobotCmds(cmd)
        robot.last_mow_cmd = self._checkMowMotorState(cmd, robot.last_mow_cmd)
        robot.last_mow_status = robot.last_mow_cmd
    
    def _cmdShutdown(self) -> None:
        logger.info(f'Send command to robot: shutdown')
        robot.status_tmp_timestamp = datetime.now()
        robot.set_robot_status('shutdown', 'shutdown')
        self.setRobotCmds(sunraycommstack.shutdown())

    def _cmdReboot(self) -> None:
        logger.info(f'Send command to robot: reboot')
        robot.status_tmp_timestamp = datetime.now()
        robot.set_robot_status('reboot', 'reboot')
        self.setRobotCmds(sunraycommstack.reboot())

    def _cmdGpsReboot(self) -> None:
        logger.info(f'Send command to robot: rebootGps')
        robot.status_tmp_timestamp = datetime.now()
        robot.set_robot_status('gps reboot', 'gps reboot')
        self.setRobotCmds(sunraycommstack.gpsreboot())

    def _cmdToggleMowMowtor(self) -> None:
        logger.info(f'Send command to robot: toggleMowMotor')
        cmd = sunraycommstack.togglemowmotor()
        self.setRobotCmds(cmd)
        robot.last_mow_cmd = self._checkMowMotorState(cmd, robot.last_mow_cmd)
        robot.last_mow_status = robot.last_mow_cmd

    def _cmdSetPositionMode(self) -> None:
        logger.info(f'Send command to robot: setPositionMode')
        self.setRobotCmds(sunraycommstack.takepositionmode())
    
    def _cmdChangeMowspeed(self) -> None:
        logger.info(f'Send command to robot: changeMowSpeed')
        cmd = sunraycommstack.changespeed(robot.mowspeed_setpoint)
        self.setRobotCmds(cmd)
        robot.last_mow_cmd = self._checkMowMotorState(cmd, robot.last_mow_cmd)
        robot.last_mow_status = robot.last_mow_cmd
    
    def _cmdChangeGotoSpeed(self) -> None:
        logger.info(f'Send command to robot: changeGoToSpeed')
        cmd = sunraycommstack.changespeed(robot.gotospeed_setpoint)
        self.setRobotCmds(cmd)
        robot.last_mow_cmd = self._checkMowMotorState(cmd, robot.last_mow_cmd)
        robot.last_mow_status = robot.last_mow_cmd
    
    def _cmdSkipNextPoint(self) -> None:
        logger.info(f'Send command to robot: skipNextPoint')
        robot.status_tmp_timestamp = datetime.now()
        robot.set_robot_status('skip point', 'skip point')
        cmd = sunraycommstack.skipnextpoint()
        self.setRobotCmds(cmd)
        robot.last_mow_cmd = self._checkMowMotorState(cmd, robot.last_mow_cmd)
        robot.last_mow_status = robot.last_mow_cmd
    
    def _cmdSkipToMowProgress(self) -> None:
        logger.info(f'Send command to robot: skipToMowProgress')
        robot.status_tmp_timestamp = datetime.now()
        robot.set_robot_status(f'skip to {round(robot.mowprogress*100)}%', f'skip to {round(robot.mowprogress*100)}%')
        cmd = sunraycommstack.skiptomowprogress(robot.mowprogress)
        self.setRobotCmds(cmd)
        robot.last_mow_cmd = False
        robot.last_mow_status = False

    def _cmdCustom(self) -> None:
        logger.info(f'Send command to robot: custom')
        self.setRobotCmds(sunraycommstack.custom())

robotInterface = RobotInterface()