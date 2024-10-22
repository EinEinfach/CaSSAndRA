import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd

from ..data.mapdata import current_map
from ..data.roverdata import robot
from . import sunraycommstack
from ..data import appdata

from icecream import ic

@dataclass
class RobotInterface:
    status: str = 'ready'
    pendingRequest: str = None
    pendingRequestCnt: int = 0
    mapDataInBuffer: bool = False
    robotCmds: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    cmdFailed: bool = False
    lastLoadWithDockPath: bool = False

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
        
    
    def onRobotMessageReceived(self, message: pd.DataFrame) -> None:
        robot.set_state(message)
        self._checkPendingRequest()
    
    def performCmd(self, cmd: str) -> None:
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
        elif cmd == 'gpsReboot':
            self._cmdGpsReboot()
        elif cmd == 'changeMowSpeed':
            self._cmdChangeMowspeed()
        elif cmd == 'changeGoToSpeed':
            self._cmdChangeGotoSpeed()
        elif cmd == 'skipNextPoint':
            self._cmdSkipNextPoint()
        elif cmd == 'skipToMowProgress':
            self._cmdSkipToMowProgress
        elif cmd == 'setPositionMode':
            self._cmdSetPositionMode()
        elif cmd == 'toggleMowMotor':
            self._cmdToggleMowMowtor()
        elif cmd == 'resume':
            self._cmdResume()
        else:
            logger.warning('Server instance got unknown command')
    
    def resetRobotCmds(self) -> None:
        self.robotCmds = pd.DataFrame()

    def _cmdStop(self) -> None:
        self.status = 'stop'
        self.robotCmds = sunraycommstack.stop()
        robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
    
    def _cmdMove(self) -> None:
        self.status = 'move'
        if robot.cmd_move_lin == 0 and robot.cmd_move_ang == 0:
            self.robotCmds = pd.DataFrame()
        else:
            self.robotCmds = sunraycommstack.move([robot.cmd_move_lin, robot.cmd_move_ang]) 
    
    def _cmdTakeMap(self, way: pd.DataFrame, dockpath: bool) -> None:
        self._calcMapCrc(way, dockpath)
        self.robotCmds = sunraycommstack.takemap(current_map.perimeter, way, dockpath)
        self.mapDataInBuffer = True
    
    def _cmdGoTo(self) -> None:
        self.pendingRequest = 'goTo'
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif (abs(robot.map_crc - current_map.map_crc) < 200) and self.pendingRequestCnt > 1:
            self.robotCmds = sunraycommstack.goto()
            robot.last_cmd = self.robotCmds
            robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
            robot.current_task = current_map.gotopoint
            self.lastLoadWithDockPath = False
            self.pendingRequest = None
            return
        else:
            logger.debug(f'Current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.gotopoint, dockpath=False)
    
    def _cmdDock(self) -> None:
        self.pendingRequest = 'dock'
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif self.lastLoadWithDockPath or ((abs(robot.map_crc - current_map.map_crc) < 200) and self.pendingRequestCnt > 1):
            self.robotCmds = sunraycommstack.dock()
            robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
            robot.dock_reason = 'operator'
            robot.dock_reason_time = datetime.now()
            self.lastLoadWithDockPath = True
            self.pendingRequest = None
            return
        else:
            logger.debug(f'Current map does not contain dock path or crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.gotopoint, dockpath=True)
    
    def _cmdDockSchedule(self) -> None:
        self.robotCmds = sunraycommstack.dock()
        robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
        robot.dock_reason = 'schedule'
        robot.dock_reason_time = datetime.now()
    
    def _cmdMow(self) -> None:
        self.pendingRequest = 'mow'
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif (abs(robot.map_crc - current_map.map_crc) < 200) and self.pendingRequestCnt > 1:
            self.robotCmds = sunraycommstack.mow()
            robot.last_cmd = self.robotCmds
            robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
            robot.current_task = current_map.mowpath
            self.lastLoadWithDockPath = True
            self.pendingRequest = None
            return
        else:
            logger.debug(f'Current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.mowpath, dockpath=True)
    
    def _cmdSendMap(self) -> None:
        self.pendingRequest = 'sendMap'
        self.pendingRequestCnt += 1
        if self.pendingRequestCnt >= 5:
            self._cmdTransmissionFailed()
            self.pendingRequest = None
            self.pendingRequestCnt = 0
            logger.error(f'Map upload failed current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            return
        elif (abs(robot.map_crc - current_map.map_crc < 100)) and self.pendingRequestCnt > 1:
            self.lastLoadWithDockPath = True
            self.pendingRequest = None
        else:
            logger.debug(f'Current map crc does not match rover crc. CRC deviation: {robot.map_crc - current_map.map_crc}')
            self._cmdTakeMap(way=current_map.mowpath, dockpath=True)
                         

    def _cmdResume(self) -> None:
        self.robotCmds = sunraycommstack.resume()
        robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
    
    def _cmdShutdown(self) -> None:
        self.robotCmds = sunraycommstack.shutdown()

    def _cmdReboot(self) -> None:
        self.robotCmds = sunraycommstack.reboot()

    def _cmdGpsReboot(self) -> None:
        self.robotCmds = sunraycommstack.gpsreboot()

    def _cmdToggleMowMowtor(self) -> None:
        self.robotCmds = sunraycommstack.togglemowmotor()
        robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)

    def _cmdSetPositionMode(self) -> None:
        self.robotCmds = sunraycommstack.takepositionmode()
    
    def _cmdChangeMowspeed(self) -> None:
        self.robotCmds = sunraycommstack.changespeed(robot.mowspeed_setpoint)
        robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
    
    def _cmdChangeGotoSpeed(self) -> None:
        self.robotCmds = sunraycommstack.changespeed(robot.gotospeed_setpoint)
        robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
    
    def _cmdSkipNextPoint(self) -> None:
        self.robotCmds = sunraycommstack.skipnextpoint()
        robot.last_mow_status = self._checkMowMotorState(self.robotCmds, robot.last_mow_status)
    
    def _cmdSkipToMowProgress(self) -> None:
        self.robotCmds = sunraycommstack.skiptomowprogress(robot.mowprogress)

    def _cmdCustom(self) -> None:
        self.robotCmds = sunraycommstack.custom()

robotInterface = RobotInterface()