import logging
logger = logging.getLogger(__name__)

import pandas as pd
import math
from datetime import datetime
from dataclasses import dataclass
import os
from PIL import Image

from . import appdata
from .cfgdata import rovercfg

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
    solution: str = 'invalid'
    speed: float = 0
    mowspeed_setpoint: float = rovercfg.mowspeed_setpoint
    gotospeed_setpoint: float = rovercfg.gotospeed_setpoint
    status: str = 'offline'
    direction: float = 0
    backwards: bool = False
    timestamp = datetime.now()
    #commanded
    last_mow_status: bool = False
    cmd_move_lin: float = 0
    cmd_move_ang: float = 0
    last_cmd: pd.DataFrame = pd.DataFrame()
    current_task: pd.DataFrame = pd.DataFrame()
    #frontend
    rover_image: Image = Image.open(os.path.dirname(__file__).replace('/backend/data', '/assets/icons/rover0grad.png'))

    def set_state(self, state: pd.DataFrame()) -> None:
        state = state.iloc[-1]
        self.speed = self.calc_speed(state['position_x'], state['position_y'], self.timestamp)
        self.direction = self.calc_direction(state['position_x'], state['position_y'])
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
    
    def calc_direction(self, position_x: float, position_y: float) -> float:
        timedelta = datetime.now() - self.timestamp
        timedelta_seconds = timedelta.total_seconds()
        delta_x = position_x - self.position_x
        delta_y = position_y - self.position_y
        distance = (delta_x**2 + delta_y**2)**(1/2)
        #avoid jumping of angle
        if distance < 0.05:
            self.backwards = False
            return self.direction
        #if docked no change of angle need
        if self.job == 2:
            return self.direction
        #calc new angle
        direction_rad = math.atan2(delta_y, delta_x)
        direction_deg = round(direction_rad*(180/math.pi))
        if direction_deg < 0:
            direction_deg = round(360 + direction_deg)
        #check if time between messages to long, reset backwards movement
        if timedelta_seconds > 3:
            self.backwards = False
            return direction_deg
        #check for angular speed (if to high, then backwards movement)
        logger.debug('Calced angle speed: '+str(abs(direction_deg-self.direction)/(timedelta_seconds))+' Timedelta: '+str(timedelta_seconds))
        logger.debug('Calced angle: '+str(direction_deg))
        if (abs(direction_deg-self.direction)/(timedelta_seconds)) > 50 and self.backwards == False:
            self.backwards = True
            if direction_deg >= 180:
                direction_deg = direction_deg - 180
            else:
                direction_deg = direction_deg + 180
        elif (abs(direction_deg-self.direction)/(timedelta_seconds)) > 60 and self.backwards == True:
            self.backwards = False
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
        elif self.job == 2 and self.amps <= appdata.current_thd_charge:
            return 'charging'
        elif self.job == 2:
            return 'docked'
        elif self.job == 3:
            return 'error'
        elif self.job == 4:
            return 'docking'
        else:
            return 'unknown'
    
    def calc_soc(self) -> float:
        soc = 0+(self.battery_voltage-appdata.soc_lookup_table[0]['V'])*((100-0)/(appdata.soc_lookup_table[1]['V']-appdata.soc_lookup_table[0]['V']))
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
        absolute_path = os.path.dirname(__file__).replace('/backend/data', '/assets/icons/')
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

