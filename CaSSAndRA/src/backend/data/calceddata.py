import logging
logger = logging.getLogger(__name__)

#package imports
import pandas as pd
from datetime import datetime
from shapely.geometry import *

#local imports
from . import roverdata
from . roverdata import robot
from . cfgdata import appcfg
from . mapdata import mapping_maps

def calcdata_from_state():
    logger.debug('Backend: Calc data from state data frame')
    #create longnames
    current_df = roverdata.state.iloc[-1]
    if current_df['position_solution'] == 2:
        solution = 'fix'
    elif current_df['position_solution'] == 1:
        solution = 'float'
    else:
        solution = 'invalid'
    
    if current_df['job'] == 4:
        job = 'docking'
    elif current_df['job'] == 3:
        job = 'error'
    elif current_df['job'] == 2 and current_df['amps'] >= appcfg.current_thd_charge:
        job = 'docked'
    elif current_df['job'] == 2:
        job = 'charging'
    elif current_df['job'] == 1:
        job = 'mow'
    elif current_df['job'] == 0:
        job = 'idle'
    else:
        job = 'unknown'

    if current_df['sensor'] == 17:
        sensor = 'emergency/stop'
    elif current_df['sensor'] == 16:
        sensor = 'rain sensor'
    elif current_df['sensor'] == 15:
        sensor = 'lifted'
    elif current_df['sensor'] == 14:
        sensor = 'ultrasonic sensor'
    elif current_df['sensor'] == 13:
        sensor = 'bumpered'
    elif current_df['sensor'] == 12:
        sensor = 'memory overflow'
    elif current_df['sensor'] == 11:
        sensor = 'no route'
    elif current_df['sensor'] == 10:
        sensor = 'odometry'
    elif current_df['sensor'] == 9:
        sensor = 'gps invalid'
    elif current_df['sensor'] == 8:
        sensor = 'motor'
    elif current_df['sensor'] == 7:
        sensor = 'overload'
    elif current_df['sensor'] == 6:
        sensor = 'kidnapped'
    elif current_df['sensor'] == 5:
        sensor = 'imu tilt'
    elif current_df['sensor'] == 4:
        sensor = 'imu timeout'
    elif current_df['sensor'] == 3:
        sensor = 'gps timeout'
    elif current_df['sensor'] == 2:
        sensor = 'obstacle'
    elif current_df['sensor'] == 1:
        sensor = 'undervoltage'
    elif current_df['sensor'] == 0:
        sensor = 'no error'
    else:
        sensor = 'unknown'
    #calc soc-value
    soc = 0+(current_df['battery_voltage']-appcfg.voltage_0)*((100)/(appcfg.voltage_100-appcfg.voltage_0))
    if soc < 0:
        soc = 0
    elif soc > 100:
        soc = 100

    calced_from_state = {'solution':solution, 'job':job, 'sensor': sensor, 'soc': soc, 'timestamp': current_df['timestamp']}
    calced_from_state = pd.DataFrame(calced_from_state, index=[0])
    roverdata.calced_from_state = pd.concat([roverdata.calced_from_state, calced_from_state], ignore_index=True)

def calcdata_from_stats():
    pass
    logger.debug('Backend: Calc data from stats data frame')
    if len(roverdata.stats) > 1:   
        last2_rows = roverdata.stats.tail(2)
        last2_rows.index = [0, 1]
        last2_rows = last2_rows.drop(['timestamp'], axis=1)
        diff_df = last2_rows.diff()
        diff_df = diff_df.drop([0])
        #Last df data is smaller than 0 -> rover reset?
        if (diff_df.iloc[-1]['duration_idle'] < 0 or diff_df.iloc[-1]['duration_charge'] < 0 or diff_df.iloc[-1]['duration_mow'] < 0 
            or diff_df.iloc[-1]['duration_mow_fix'] < 0 or diff_df.iloc[-1]['duration_mow_float'] < 0 or diff_df.iloc[-1]['duration_mow_invalid'] < 0):
            diff_df = roverdata.stats.tail(1)
        diff_df.loc[:,'timestamp'] = roverdata.stats.iloc[-1]['timestamp']
        calced_from_stats = diff_df
        roverdata.calced_from_stats = pd.concat([roverdata.calced_from_stats, calced_from_stats], ignore_index=True)
    else:
        logger.warning('Backend: Could not write calc from stats data to data frame. Skipping')

def calc_rover_state():
    #check if rover online
    last_rover_state = robot.status
    if last_rover_state != 'offline':
        last_timestamp = robot.timestamp
        now = datetime.now()
        difference = now - last_timestamp
        difference = difference.total_seconds()
        if difference > appcfg.time_to_offline:
            logger.warning('Backend: Could not connect to the rover. State set to offline')
            robot.status = 'offline'
            calced_from_state = {'solution':'invalid', 'job':'offline', 'sensor': 'no error', 'timestamp': str(now)}
            calced_from_state = pd.DataFrame(calced_from_state, index=[0])
            roverdata.calced_from_state = pd.concat([roverdata.calced_from_state, calced_from_state], ignore_index=True)

def calc_mow_progress(mowpath: pd.DataFrame(), idx: int) -> list():
    try: 
        filtered = mowpath[mowpath['type'] == 'way']
        if idx < 0:
            idx = 0
        path_finished = filtered[filtered.index < idx]
        path_finished = path_finished[['X', 'Y']]
        try:
            path_finished = LineString(path_finished.to_numpy())
            path_finished = round(path_finished.length)
        except:
            path_finished = 0
        path = filtered[['X', 'Y']]
        path = LineString(path.to_numpy())
        path = round(path.length)
        path_finished_perc = round((path_finished/path)*100)
        idx_finished_pers = round((idx/len(filtered))*100)
        return path_finished, path, path_finished_perc, idx, len(filtered), idx_finished_pers
    except Exception as e:
        logger.warning('Backend: Calculation of mow progress failed')
        logger.debug(str(e))
        return 0, 0, 0, 0, 0, 0
    



    






    

