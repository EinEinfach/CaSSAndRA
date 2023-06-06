import logging
logger = logging.getLogger(__name__)

import pandas as pd
import math
from datetime import datetime
from dataclasses import dataclass

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
    timestamp = datetime.now()
    #commanded
    last_mow_status: bool = False
    cmd_move_lin: float = 0
    cmd_move_ang: float = 0
    last_cmd: pd.DataFrame = pd.DataFrame()
    current_task: pd.DataFrame = pd.DataFrame()

    def set_state(self, state: pd.DataFrame()) -> None:
        state = state.iloc[-1]
        self.speed = self.calc_speed(state['position_x'], state['position_y'], self.timestamp)
        self.direction = self.calc_direction(state['position_x'], state['position_y'])
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
            timedelta_seconds = timedelta.seconds + timedelta.microseconds*1000000
            speed = round(delta_distance/timedelta_seconds, 2)
        else:
            speed = 0
        return speed
    
    def calc_direction(self, position_x: float, position_y: float) -> float:
        delta_x = position_x - self.position_x
        delta_y = position_y - self.position_y
        direction_rad = math.atan2(delta_y, delta_x)
        direction_deg = round(direction_rad*(180/math.pi))
        if direction_deg < 0:
            direction_deg = round(360 + direction_deg)
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
            
#define robot instancs
robot = Mower()

#measured
state = pd.DataFrame()
stats = pd.DataFrame()
props = pd.DataFrame()
online = pd.DataFrame()

#calced
calced_from_state = pd.DataFrame()
calced_from_stats = pd.DataFrame()






