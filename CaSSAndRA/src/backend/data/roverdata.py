import logging
logger = logging.getLogger(__name__)

import pandas as pd
import math
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import os
from PIL import Image
from icecream import ic

from . import appdata
from . cfgdata import rovercfg, appcfg, commcfg
#from .. comm.api import cassandra_api

#mower class
@dataclass
class Mower:
    fw: str = None
    fw_version: str = None
    uptoday: bool = False
    battery_voltage: float = 0.0
    position_x: float = 0.0
    position_y: float = 0.0
    position_delta: float = 0.0
    position_solution: int = 0
    job: int  = 10
    position_mow_point_index: int = 0
    position_age: float = 0.0
    sensor: int = 0
    target_x: float = 0.0
    target_y: float = 0.0
    position_accuracy: float = 0.0
    position_visible_satellites: int = 0
    amps: float = 0.0
    position_visible_satellites_dgps: int = 0
    map_crc: int = 0
    lateral_error: float = 0.0
    soc: int = 0
    speed: float = 0.0
    average_speed: float = rovercfg.mowspeed_setpoint/2
    mowspeed_setpoint: float = rovercfg.mowspeed_setpoint
    gotospeed_setpoint: float = rovercfg.gotospeed_setpoint
    direction: float = 0.0
    backwards: bool = False
    timestamp: datetime = datetime.now()
    #commanded
    last_mow_cmd: bool = False
    last_mow_status: bool = False
    cmd_move_lin: float = 0.0
    cmd_move_ang: float = 0.0
    last_cmd: pd.DataFrame = field(default_factory=lambda: pd.DataFrame([{'msg': 'AT+C,-1,-1,-1,-1,-1,-1,-1,-1'}]))
    last_task_name: str = 'no task'
    current_task: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    map_old_crc: int = None
    mowprogress: float = 0.0
    last_position_mow_point_index: int = None
    measured_time_since_last_position_index_change = None
    seconds_per_idx: float = None
    #frontend
    rover_image: Image = field(default_factory = lambda: 
                               Image.open(os.path.dirname(__file__).replace('/backend/data', '/assets/icons/'+appcfg.rover_picture+'rover0grad.png')))
    solution: str = 'invalid'
    status: str = 'offline'
    status_tmp: str = 'offline'
    status_tmp_timestamp: datetime = datetime.now()
    sensor_status: str = 'unknown'
    position_age_hr = '99+d'
    dock_reason: str = None
    dock_reason_time: datetime = datetime.now()

    def set_props(self, props: pd.DataFrame) -> None:
        props = props.iloc[-1]
        self.fw = props['firmware']
        self.fw_version = props['version']

    def set_state(self, state: pd.DataFrame) -> None:
        state = state.iloc[-1]
        self.speed = self.calc_speed(state['position_x'], state['position_y'], self.timestamp)
        self.direction = self.calc_direction()
        self.rover_image = self.set_rover_image()
        self.battery_voltage = round(state['battery_voltage'], 2)
        self.position_x = round(state['position_x'], 2)
        self.position_y = round(state['position_y'], 2)
        self.position_delta = state['position_delta']
        self.position_solution = state['position_solution']
        self.job = state['job']
        self.position_mow_point_index = state['position_mow_point_index']
        self.position_age = round(state['position_age'], 2)
        self.sensor = state['sensor']
        self.target_x = round(state['target_x'], 2)
        self.target_y = round(state['target_y'], 2)
        self.position_accuracy = round(state['position_accuracy'], 2)
        self.position_visible_satellites = state['position_visible_satellites']
        self.amps = round(state['amps'], 2)
        self.position_visible_satellites_dgps = state['position_visible_satellites_dgps']
        self.map_crc = state['map_crc']
        self.lateral_error = state['lateral_error']
        self.soc = self.calc_soc()
        self.solution = self.calc_solution()
        self.timestamp = datetime.now()
        self.check_dock_reason()
        self.set_robot_status(self.calc_status())
        self.sensor_status = self.calc_sensor_status()
        self.position_age_hr = self.calc_position_age_hr()
        self.calc_seconds_per_idx()
        self.uptoday = True
    
    def calc_speed(self, position_x: float, position_y: float, timestamp) -> float:
        if self.job == 1 or self.job == 4:
            delta_x = position_x - self.position_x
            delta_y = position_y - self.position_y
            delta_distance = (delta_x**2+delta_y**2)**(1/2)
            timedelta = datetime.now() - timestamp
            timedelta_seconds = timedelta.total_seconds()
            speed = round(delta_distance/timedelta_seconds, 2)
            self.average_speed = 0.999*self.average_speed + 0.001*speed
        else:
            speed = 0.0
        return speed
    
    def calc_direction(self) -> float:
        if self.position_delta < 0:
            direction_rad = self.position_delta + 2*math.pi
        else:
            direction_rad = self.position_delta
        direction_deg = round(direction_rad*(180/math.pi))
        return direction_deg

    def calc_status(self) -> str:
        if (datetime.now() - self.status_tmp_timestamp).seconds < 10:
            return self.status_tmp
        elif (datetime.now()-self.timestamp).seconds > 60:
            return 'offline'
        elif self.job == 0:
            return 'idle'
        elif self.job == 1 and self.last_mow_status == False:
            return 'transit'
        elif self.job == 1 and self.last_mow_status == True:
            return 'mow'
        elif self.job == 2 and self.amps <= appcfg.current_thd_charge:
            return 'charging'
        elif self.job == 2:
            return 'docked'
        elif self.job == 3:
            return 'error'
        elif self.job == 4:
            return 'docking'
        else:
            return 'unknown'
    
    def calc_sensor_status(self) -> str:
        if self.job == 3:
            if self.sensor == 18:
                return 'temperature out of range'
            elif self.sensor == 17:
                return 'emergency/stop'
            elif self.sensor == 16:
                return 'rain sensor'
            elif self.sensor == 15:
                return 'lifted'
            elif self.sensor == 14:
                return 'sonar error'
            elif self.sensor == 13:
                return 'bumper error'
            elif self.sensor == 12:
                return 'memory error'
            elif self.sensor == 11:
                return 'no route'
            elif self.sensor == 10:
                return 'odo error'
            elif self.sensor == 9:
                return 'gps invalid'
            elif self.sensor == 8:
                return 'motor error'
            elif self.sensor == 7:
                return 'overload'
            elif self.sensor == 6:
                return 'kidnapped'
            elif self.sensor == 5:
                return 'imu tilt'
            elif self.sensor == 4:
                return 'imu timeout'
            elif self.sensor == 3:
                return 'gps timeout'
            elif self.sensor == 2:
                return 'obstacle'
            elif self.sensor == 1:
                return 'undervoltage'
            elif self.sensor == 0:
                return 'no error'
            else:
                return 'unknown'
        elif self.dock_reason != None:
            return self.dock_reason
        else:
            if len(self.sensor_status) >= 5:
                return '.'
            elif len(self.sensor_status) == 4:
                return '.....'
            elif len(self.sensor_status) == 3:
                return '....'
            elif len(self.sensor_status) == 2:
                return '...'
            elif len(self.sensor_status) == 1:
                return '..'
    
    def calc_position_age_hr(self) -> str:
        if self.position_age >= 356400:
            return '99+d'
        if self.position_age >= 86400:
            return str(round(self.position_age//86400))+'d'
        elif self.position_age >=3600:
            return str(round(self.position_age//3600))+'h'
        elif self.position_age >=60:
            return str(round(self.position_age//60))+'min'
        else:
            return str(self.position_age)+'s'

    def calc_soc(self) -> float:
        soc = 0+(self.battery_voltage-appcfg.voltage_0)*((100-0)/(appcfg.voltage_100-appcfg.voltage_0))
        if soc < 0:
            soc = 0
        elif soc > 100:
            soc = 100  
        return round(soc)  
    
    def calc_solution(self) -> str:
        if self.position_solution == 2:
            return 'fix'
        elif self.position_solution == 1:
            return 'float'
        else:
            return 'invalid'
    
    def change_speed(self, choise: str, speeddiff: float) -> None:
        if choise == 'mow':
            new_setpoint = round(self.mowspeed_setpoint + speeddiff, 2)
            new_setpoint = max(0, new_setpoint)
            self.mowspeed_setpoint = min(1, new_setpoint)
        elif choise == 'goto':
            new_setpoint = round(self.gotospeed_setpoint + speeddiff, 2)
            new_setpoint = max(0, new_setpoint)
            self.gotospeed_setpoint = min(1, new_setpoint)
    
    def set_rover_image(self) -> None:
        return Image.Image.rotate(appcfg.rover_pictures, self.direction, resample=Image.BICUBIC)
            
    def check_dock_reason(self) -> None:
        if self.job == 4: 
            if self.dock_reason != None:
                pass
            elif self.sensor == 18:
                self.dock_reason = 'temperature'
            elif self.sensor == 16:
                self.dock_reason = 'rain'
            elif robot.position_mow_point_index == 0:
                self.dock_reason = 'finished'
            else:
                self.dock_reason = 'low battery'
            self.dock_reason_time = datetime.now()
        elif (self.job == 2 and (datetime.now() - self.dock_reason_time).seconds >= 3600) or (self.job != 4 and self.job != 2):
            self.dock_reason = None
            self.dock_reason_time = datetime.now()
    
    def set_robot_status(self, status: str, status_tmp = None) -> None:
        # set mow status to false if docking triggered (avoid wrong state if docking triggered from sunray fw)
        if self.status != 'docking' and status == 'docking':
            self.last_mow_status = False
        # set status and tmp status
        self.status = status
        if status_tmp != None:
            self.status_tmp = status_tmp
    
    def calc_seconds_per_idx(self) -> None:
        # # based on history data, make problems on slow machines
        # start_point = datetime.now() - timedelta(days=1)
        # try:
        #     relevant_data = state
        #     relevant_data['timestamp'] = pd.to_datetime(relevant_data['timestamp'])
        #     relevant_data = state[(state['timestamp'] >= start_point) & (state['job'] == 1) & (state['position_solution'] == 2)]
        #     relevant_data.loc[:,'position_mow_point_index'] = relevant_data['position_mow_point_index'].diff()
        #     relevant_data = relevant_data[relevant_data['position_mow_point_index'] > 0]
        #     relevant_data.loc[:,'timestamp'] = relevant_data['timestamp'].diff()
        #     relevant_data.loc[:,'timestamp'] = relevant_data['timestamp'].dt.total_seconds()
        #     relevant_data.loc[:,'timestamp'] = relevant_data['timestamp']/relevant_data['position_mow_point_index']
        #     relevant_data = relevant_data[relevant_data['timestamp'] < 300]
        #     if len(relevant_data) < 50:
        #         return
        #     test = relevant_data['timestamp'].mean()

        # except Exception as e:
        #     logger.warning('Could not create estimation time, data in state data frame are invalid')
        #     logger.debug(f'{e}')

        # based on current data
        current_seconds_per_idx = None
        if (self.status == 'mow' and self.last_position_mow_point_index == None and self.measured_time_since_last_position_index_change == None):
            self.last_position_mow_point_index = self.position_mow_point_index
            self.measured_time_since_last_position_index_change = datetime.now()
        elif (self.status == 'mow'):
            idx_delta =  self.position_mow_point_index - self.last_position_mow_point_index
            time_delta = (datetime.now() - self.measured_time_since_last_position_index_change).seconds
            if (idx_delta > 0):
                current_seconds_per_idx = time_delta/idx_delta
        else:
            self.last_position_mow_point_index = None
            self.measured_time_since_last_position_index_change = None

        if (current_seconds_per_idx != None and current_seconds_per_idx < 300):
            if (self.seconds_per_idx == None):
                self.seconds_per_idx = current_seconds_per_idx
            else:
                self.seconds_per_idx = 0.999 * self.seconds_per_idx+0.001 * current_seconds_per_idx
        if (current_seconds_per_idx != None):
            self.last_position_mow_point_index = self.position_mow_point_index
            self.measured_time_since_last_position_index_change = datetime.now()

#define robot instance
robot = Mower()

#measured
state = pd.DataFrame()
stats = pd.DataFrame()
props = pd.DataFrame()
online = pd.DataFrame()

#calced
calced_from_state = pd.DataFrame()
calced_from_stats = pd.DataFrame()

