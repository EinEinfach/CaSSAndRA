import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
import json, time
import pandas as pd

from ...data.roverdata import robot
from ...data.mapdata import current_map, current_task
from ...data.cfgdata import pathplannercfgapi
from ... map import path, map
from ..robotinterface import robotInterface

@dataclass
class RobotTopic:
    robotstate: dict = field(default_factory=lambda: dict())
    robotstateJson: str = '{}'
    allowedCmds: list = field(default_factory=lambda: ['mow', 'stop', 'dock', 'move', 'reboot', 'rebootGps', 'shutdown', 'setMowSpeed', 'setGoToSpeed', 'setMowProgress', 'goTo', 'toggleMowMotor', 'skipNextPoint'])
    allowedMowCmdVal: list = field(default_factory=lambda: ['resume', 'task', 'all', 'selection'])
    mapData: dict = field(default_factory=lambda: dict())
    
    def createPayload(self) -> dict:
        try:
            self.robotstate['firmware'] = robot.fw
            self.robotstate['version'] = robot.fw_version
            self.robotstate['status'] = robot.status
            self.robotstate['dockReason'] = robot.dock_reason
            self.robotstate['sensorState'] = robot.sensor_status
            self.robotstate['battery'] = dict(soc=robot.soc, voltage=robot.battery_voltage, electricCurrent=robot.amps)
            self.robotstate['position'] = dict(x=robot.position_x, y=robot.position_y)
            self.robotstate['target'] = dict(x=robot.target_x, y=robot.target_y) 
            self.robotstate['angle'] = robot.position_delta
            self.robotstate['mowPointIdx'] = int(robot.position_mow_point_index)
            self.robotstate['gps'] = dict(visible = int(robot.position_visible_satellites), dgps=int(robot.position_visible_satellites_dgps), age=robot.position_age_hr, solution= robot.solution)
            self.robotstate['secondsPerIdx'] = robot.seconds_per_idx
            self.robotstate['speed'] = robot.speed
            self.robotstate['averageSpeed'] = robot.average_speed
            self.robotstate['mowMotorActive'] = robot.last_mow_status
            self.robotstateJson = json.dumps(self.robotstate)
            return self.robotstateJson
        except Exception as e:
            logger.error('Could not create api robot payload.')
            logger.error(str(e))
            return dict()
    
    def checkCmd(self, buffer: dict) ->  None:
        try:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedCmds))
            if command == []:
                logger.info(f'No valid command in api message for robot topic found. Allowed commands: {self.allowedCmds}. Aborting')
            else:
                self._performCmd(command[0], buffer)
        except Exception as e:
            logger.error('Api command for robot topic is invalid')
            logger.error(str(e))
    
    def _performCmd(self, command: str, buffer: dict) -> None:
        try:
            if command == 'stop':
                robotInterface.performCmd('stop')
            elif command == 'dock':
                robotInterface.performCmd('dock')
            elif command == 'mow':
                self._mow(buffer)
            elif command == 'goTo':
                self._goTo(buffer)
            elif command == 'move':
                robot.cmd_move_lin = buffer['value'][0]
                robot.cmd_move_ang = buffer['value'][1]
                robotInterface.performCmd('move')
            elif command == 'reboot':
                robotInterface.performCmd('reboot')
            elif command == 'rebootGps':
                robotInterface.performCmd('rebootGps')
            elif command == 'shutdown':
                robotInterface.performCmd('shutdown')
                self.check_auto_shutdown = True
            elif command == 'setMowSpeed':
                robot.mowspeed_setpoint = buffer['value'][0]
                robotInterface.performCmd('changeMowSpeed')
            elif command == 'setGoToSpeed':
                robot.gotospeed_setpoint = buffer['value'][0]
                robotInterface.performCmd('changeGoToSpeed')
            elif command == 'setMowProgress':
                robot.mowprogress = buffer['value'][0]
                robotInterface.performCmd('skipToMowProgress')
            elif command == 'toggleMowMotor':
                robotInterface.performCmd('toggleMowMotor')
            elif command == 'skipNextPoint':
                robotInterface.performCmd('stop')
                robotInterface.performCmd('skipNextPoint')
                time.sleep(3)
                robotInterface.performCmd('resume')
        except Exception as e:
            logger.error(f'Api value for robot command is invalid')
            logger.debug(f'{e}')
    
    def _mow(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            value = list(set(value).intersection(self.allowedMowCmdVal))
            if value == []:
                logger.info(f'No valid value in api message for robot mow command found. Allowed values: {self.allowedMowCmdVal}. Aborting')
                return
            if value[0] == 'resume':
                current_map.reset_route_mowpath()
                robotInterface.performCmd('resume')
            elif value [0] == 'task': 
                current_map.task_progress = 0
                current_map.calculating = True
                path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
                current_map.calculating = False
                current_map.calc_route_mowpath()
                robotInterface.performCmd('mow')
            elif value[0] == 'all':
                current_map.selected_perimeter = current_map.perimeter_polygon
                current_map.calculating = True
                current_map.task_progress = 0
                current_map.total_tasks = 1
                route = path.calc_simple(current_map.selected_perimeter, pathplannercfgapi)
                current_map.calc_route_preview(route) 
                current_map.areatomow = round(current_map.selected_perimeter.area)
                current_map.calculating = False
                current_map.calc_route_mowpath()
                robotInterface.performCmd('mow')
            elif value[0] == 'selection':
                current_map.selected_perimeter = map.selection(current_map.perimeter_polygon, self.mapData['selection'])
                current_map.calculating = True
                current_map.task_progress = 0
                current_map.total_tasks = 1
                route = path.calc_simple(current_map.selected_perimeter, pathplannercfgapi)
                current_map.calc_route_preview(route)
                current_map.areatomow = round(current_map.selected_perimeter.area)
                current_map.calculating = False
                current_map.calc_route_mowpath()
                robotInterface.performCmd('mow')

        except Exception as e:
            logger.error('Api value for mow robot command invalid')
            logger.error(str(e))
    
    def _goTo(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            current_map.gotopoint = pd.DataFrame(value)
            current_map.gotopoint.columns = ['X', 'Y']
            current_map.gotopoint['type'] = 'way'
            current_map.clear_route_mowpath()
            robotInterface.performCmd('goTo')
        except Exception as e:
            logger.error('Api value for go to robot command invalid')
            logger.error(str(e))

robotTopic = RobotTopic()
        