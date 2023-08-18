import logging
logger = logging.getLogger(__name__)

import pandas as pd
import math
from datetime import datetime
from dataclasses import dataclass
import os
from PIL import Image

from . import appdata
from .cfgdata import rovercfg, appcfg

#mower class
@dataclass
class Mower:
    battery_voltage: float = 0
    position_x: float = 0
    position_y: float = 0
    position_delta: float = 0
    position_solution: int = 0
    job: int  = 10
    position_mow_point_index: int = 0
    position_age: float = 0
    sensor: int = 0
    target_x: float = 0
    target_y: float = 0
    position_accuracy: float = 0
    position_visible_satellites: int = 0
    amps: float = 0
    position_visible_satellites_dgps: int = 0
    map_crc: int = 0
    soc: float = 0
    speed: float = 0
    mowspeed_setpoint: float = rovercfg.mowspeed_setpoint
    gotospeed_setpoint: float = rovercfg.gotospeed_setpoint
    direction: float = 0
    backwards: bool = False
    timestamp = datetime.now()
    #commanded
    last_mow_status: bool = False
    cmd_move_lin: float = 0
    cmd_move_ang: float = 0
    last_cmd: pd.DataFrame = pd.DataFrame([{'msg': 'AT+C,-1,-1,-1,-1,-1,-1,-1,-1'}])
    last_task_name: str = 'no task'
    current_task: pd.DataFrame = pd.DataFrame()
    #frontend
    rover_image: Image = Image.open(os.path.dirname(__file__).replace('/backend/data', '/assets/icons/'+appcfg.rover_picture+'rover0grad.png'))
    solution: str = 'invalid'
    status: str = 'offline'
    sensor_status: str = 'unknown'
    position_age_hr = '99+d'

    def set_state(self, state: pd.DataFrame()) -> None:
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
        self.soc = self.calc_soc()
        self.solution = self.calc_solution()
        self.timestamp = datetime.now()
        self.status = self.calc_status()
        self.sensor_status = self.calc_sensor_status()
        self.position_age_hr = self.calc_position_age_hr()
    
    def calc_speed(self, position_x: float, position_y: float, timestamp) -> float:
        if self.job == 1 or self.job == 4:
            delta_x = position_x - self.position_x
            delta_y = position_y - self.position_y
            delta_distance = (delta_x**2+delta_y**2)**(1/2)
            timedelta = datetime.now() - timestamp
            timedelta_seconds = timedelta.total_seconds()
            speed = round(delta_distance/timedelta_seconds, 2)
        else:
            speed = 0
        return speed
    
    def calc_direction(self) -> float:
        if self.position_delta < 0:
            direction_rad = self.position_delta + 2*math.pi
        else:
            direction_rad = self.position_delta
        direction_deg = round(direction_rad*(180/math.pi))
        return direction_deg

    def calc_status(self) -> str():
        if (datetime.now()-self.timestamp).seconds > 60:
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
    
    def calc_sensor_status(self) -> str():
        if self.job == 3:
            if self.sensor == 17:
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
    
    def calc_solution(self) -> str():
        if self.position_solution == 2:
            return 'fix'
        elif self.position_solution == 1:
            return 'float'
        else:
            return 'invalid'
    
    def change_speed(self, choise: str(), speeddiff: float) -> None:
        if choise == 'mow':
            new_setpoint = round(self.mowspeed_setpoint + speeddiff, 2)
            new_setpoint = max(0, new_setpoint)
            self.mowspeed_setpoint = min(1, new_setpoint)
        elif choise == 'goto':
            new_setpoint = round(self.gotospeed_setpoint + speeddiff, 2)
            new_setpoint = max(0, new_setpoint)
            self.gotospeed_setpoint = min(1, new_setpoint)
    
    def set_rover_image(self) -> None:
        absolute_path = os.path.dirname(__file__).replace('/backend/data', '/assets/icons/'+appcfg.rover_picture)
        if self.direction < 7.5 or self.direction >= 352.5:
            return Image.open(absolute_path+'rover0grad.png')
        elif self.direction >= 7.5 and self.direction < 22.5:
            return Image.open(absolute_path+'rover15grad.png') 
        elif self.direction >= 22.5 and self.direction < 37.5:
            return Image.open(absolute_path+'rover30grad.png') 
        elif self.direction >= 37.5 and self.direction < 52.5:
            return Image.open(absolute_path+'rover45grad.png') 
        elif self.direction >= 52.5 and self.direction < 67.5:
            return Image.open(absolute_path+'rover60grad.png') 
        elif self.direction >= 67.5 and self.direction < 82.5:
            return Image.open(absolute_path+'rover75grad.png') 
        elif self.direction >= 82.5 and self.direction < 97.5:
            return Image.open(absolute_path+'rover90grad.png') 
        elif self.direction >= 97.5 and self.direction < 112.5:
            return Image.open(absolute_path+'rover105grad.png') 
        elif self.direction >= 112.5 and self.direction < 127.5:
            return Image.open(absolute_path+'rover120grad.png') 
        elif self.direction >= 127.5 and self.direction < 142.5:
            return Image.open(absolute_path+'rover135grad.png') 
        elif self.direction >= 142.5 and self.direction < 157.5:
            return Image.open(absolute_path+'rover150grad.png') 
        elif self.direction >= 157.5 and self.direction < 172.5:
            return Image.open(absolute_path+'rover165grad.png') 
        elif self.direction >= 172.5 and self.direction < 187.5:
            return Image.open(absolute_path+'rover180grad.png') 
        elif self.direction >= 187.5 and self.direction < 202.5:
            return Image.open(absolute_path+'rover195grad.png') 
        elif self.direction >= 202.5 and self.direction < 217.5:
            return Image.open(absolute_path+'rover210grad.png') 
        elif self.direction >= 217.5 and self.direction < 232.5:
            return Image.open(absolute_path+'rover225grad.png') 
        elif self.direction >= 232.5 and self.direction < 247.5:
            return Image.open(absolute_path+'rover240grad.png') 
        elif self.direction >= 247.5 and self.direction < 262.5:
            return Image.open(absolute_path+'rover255grad.png') 
        elif self.direction >= 262.5 and self.direction < 277.5:
            return Image.open(absolute_path+'rover270grad.png') 
        elif self.direction >= 277.5 and self.direction < 292.5:
            return Image.open(absolute_path+'rover285grad.png') 
        elif self.direction >= 292.5 and self.direction < 307.5:
            return Image.open(absolute_path+'rover300grad.png') 
        elif self.direction >= 307.5 and self.direction < 322.5:
            return Image.open(absolute_path+'rover315grad.png') 
        elif self.direction >= 322.5 and self.direction < 337.5:
            return Image.open(absolute_path+'rover330grad.png')
        elif self.direction >= 337.5 and self.direction < 352.5:
            return Image.open(absolute_path+'rover345grad.png')  
        elif self.direction >= 352.5:
            return Image.open(absolute_path+'rover0grad.png') 
        else:
            return Image.open(absolute_path+'rover0grad.png')
            
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

