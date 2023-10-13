import logging
logger = logging.getLogger(__name__)

#packege imports
import pandas as pd
from datetime import datetime
from shapely import Polygon

#local imports
from . import roverdata, calceddata
from . roverdata import robot
from . mapdata import current_map
from . cfgdata import appcfg

def create_obstacle(data: list) -> pd.DataFrame:
    list_for_df = []
    number_of_points = data[0]
    del data[0]
    for i in range(number_of_points):
        list_for_df.append([data[2*i], data[2*i+1]])
    list_for_df.append([data[0], data[1]])
    center = list(Polygon(list_for_df).centroid.coords)
    center_df = pd.DataFrame(center)
    center_df.columns = ['X', 'Y']
    center_df['type'] = 'center'
    obstacle_df = pd.DataFrame(list_for_df)
    obstacle_df.columns = ['X', 'Y']
    obstacle_df['type'] = 'points'
    obstacle_df = pd.concat([obstacle_df, center_df], ignore_index=True)
    obstacleCRCx = obstacle_df['X']*100 
    obstacleCRCy = obstacle_df['Y']*100 
    obstacle_CRC = int(obstacleCRCx.sum() + obstacleCRCy.sum())
    obstacle_df['CRC'] = obstacle_CRC
    return obstacle_df

#Add data from MQTT conection
def add_state_to_df_from_mqtt(data: dict()) -> None:
    try: 
        state_to_df = {'battery_voltage':data['battery_voltage'],
                    'position_x':data['position']['x'],
                    'position_y':data['position']['y'],
                    'position_delta':data['position']['delta'],
                    'position_solution':data['position']['solution'],
                    'job':data['job'],
                    'position_mow_point_index':data['position']['mow_point_index'],
                    'position_age':data['position']['age'],
                    'sensor':data['sensor'],
                    'target_x':data['target']['x'],
                    'target_y':data['target']['y'],
                    'position_accuracy':data['position']['accuracy'],
                    'position_visible_satellites':data['position']['visible_satellites'],
                    'amps':data['amps'],
                    'position_visible_satellites_dgps':data['position']['visible_satellites_dgps'],
                    'map_crc':data['map_crc'],
                    'lateral_error': 0,
                    'timetable_autostartstop_dayofweek': 0,
                    'timetabel_autostartstop_hour' : 0,
                    'timestamp': str(datetime.now())}
        state_to_df = pd.DataFrame(data=state_to_df, index=[0])
        robot.set_state(state_to_df)
        roverdata.state = pd.concat([roverdata.state, state_to_df], ignore_index=True)
        calceddata.calcdata_from_state()
    except Exception as e:
        logger.error('Backend: Failed to write state data to data frame')
        logger.debug(str(e))
    

def add_props_to_df_from_mqtt(data: dict()) -> None:
    try: 
        props_to_df = {'firmware':data['firmware'],
                    'version':data['version'],
                    'timestamp': str(datetime.now())
                    }
        props_to_df = pd.DataFrame(data=props_to_df, index=[0])
        roverdata.props = pd.concat([roverdata.props, props_to_df], ignore_index=True)
    except:
        logger.warning('Backend: Received props message is not valid and will be ignored')

def add_stats_to_df_from_mqtt(data: dict()) -> None:
    try: 
        stats_to_df = {'duration_idle':data['duration_idle'],
                    'duration_charge':data['duration_charge'],
                    'duration_mow':data['duration_mow'],
                    'duration_mow_invalid':data['duration_mow_invalid'],
                    'duration_mow_float':data['duration_mow_float'],
                    'duration_mow_fix':data['duration_mow_fix'],
                    'distance_mow_traveled':data['distance_mow_traveled'],
                    'counter_gps_chk_sum_errors':data['counter_gps_chk_sum_errors'],
                    'counter_dgps_chk_sum_errors':data['counter_dgps_chk_sum_errors'],
                    'counter_invalid_recoveries':data['counter_invalid_recoveries'],
                    'counter_float_recoveries':data['counter_float_recoveries'],
                    'counter_gps_jumps':data['counter_gps_jumps'],
                    'counter_gps_motion_timeout':data['counter_gps_motion_timeout'],
                    'counter_imu_triggered':data['counter_imu_triggered'],
                    'counter_sonar_triggered':data['counter_sonar_triggered'],
                    'counter_bumper_triggered':data['counter_bumper_triggered'],
                    'counter_obstacles':data['counter_obstacles'],
                    'time_max_cycle':data['time_max_cycle'],
                    'time_max_dpgs_age':data['time_max_dpgs_age'],
                    'serial_buffer_size':data['serial_buffer_size'],
                    'free_memory':data['free_memory'],
                    'reset_cause':data['reset_cause'],
                    'temp_min':data['temp_min'],
                    'temp_min':data['temp_min'],
                    'duration_mow_motor_recovery': 0,
                    'timestamp': str(datetime.now())}
        stats_to_df = pd.DataFrame(data=stats_to_df, index=[0])
        roverdata.stats = pd.concat([roverdata.stats, stats_to_df], ignore_index=True)
        calceddata.calcdata_from_stats()
    except Exception as e:
        logger.error('Backend: Failed to write stats data to data frame')
        logger.debug(str(e))

def add_online_to_df_from_mqtt(data: str()) -> None:
    if 'true' in data:
        online_to_df = {'online': True,
                            'timestamp': str(datetime.now())}
        online_to_df = pd.DataFrame(data=online_to_df, index=[0])
        roverdata.online = pd.concat([roverdata.online, online_to_df], ignore_index=True)
    elif 'false' in data:
        online_to_df = {'online': False,
                            'timestamp': str(datetime.now())}
        online_to_df = pd.DataFrame(data=online_to_df, index=[0])
        roverdata.online = pd.concat([roverdata.online, online_to_df], ignore_index=True)
    else:
        logger.warning('Backend: Received online message is not valid and will be ignored')
    

#Add data from HTTP and UART conection
def add_state_to_df(data: str()) -> None:
    try: 
        data_list = data.split(',')
        del data_list[-1]
        del data_list[0]
        #handle old AT+S strings (older than 1.0.264)
        if len(data_list) < 17:
            logger.debug('AT+S string to short, add dummy lateral error')
            data_list.append('0')
        #handle old AT+S strings (older than 1.0.3XX)
        if len(data_list) < 19:
            logger.debug('AT+S string to short, add dummy timetable day of week and timetable hour')
            data_list.append('0')
            data_list.append('0')
        data_list = [float(x) if '.' in x else int(x) for x in data_list]
        data_list.append(str(datetime.now()))
        state_to_df = pd.DataFrame([data_list])
        state_to_df.columns = ['battery_voltage',
                            'position_x',
                            'position_y',
                            'position_delta',
                            'position_solution',
                            'job',
                            'position_mow_point_index',
                            'position_age',
                            'sensor',
                            'target_x',
                            'target_y',
                            'position_accuracy',
                            'position_visible_satellites',
                            'amps',
                            'position_visible_satellites_dgps',
                            'map_crc',
                            'lateral_error',
                            'timetable_autostartstop_dayofweek',
                            'timetabel_autostartstop_hour',
                            'timestamp']
        robot.set_state(state_to_df)
        roverdata.state = pd.concat([roverdata.state, state_to_df], ignore_index=True)
        calceddata.calcdata_from_state()
    except Exception as e:
        logger.error('Backend: Failed to write state data to data frame')
        logger.debug(str(e))

def add_stats_to_df(data: str()) -> None:
    try: 
        data_list = data.split(',')
        del data_list[-1]
        del data_list[0]
        #handle old AT+T strings (older then 1.0.3XX)
        if len(data_list) < 25:
            data_list.append('0')
        data_list = [float(x) if '.' in x else int(x) for x in data_list]
        data_list.append(str(datetime.now()))
        stats_to_df = pd.DataFrame([data_list])
        stats_to_df.columns = [
                                'duration_idle',
                                'duration_charge',
                                'duration_mow',
                                'duration_mow_float',
                                'duration_mow_fix',
                                'counter_float_recoveries',
                                'distance_mow_traveled',
                                'time_max_dpgs_age',
                                'counter_imu_triggered',
                                'temp_min',
                                'temp_max',
                                'counter_gps_chk_sum_errors',
                                'counter_dgps_chk_sum_errors',
                                'time_max_cycle',
                                'serial_buffer_size',
                                'duration_mow_invalid',
                                'counter_invalid_recoveries',
                                'counter_obstacles',
                                'free_memory',
                                'reset_cause',
                                'counter_gps_jumps',
                                'counter_sonar_triggered',
                                'counter_bumper_triggered',
                                'counter_gps_motion_timeout',
                                'duration_mow_motor_recovery',
                                'timestamp'
                            ]
        roverdata.stats = pd.concat([roverdata.stats, stats_to_df], ignore_index=True)
        calceddata.calcdata_from_stats()
    except Exception as e:
        logger.error('Backend: Failed to write stats data to data frame')
        logger.debug(str(e))

def add_props_to_df_from_http(data: str()) -> None:
    pass

def add_online_to_df_from_http(data: bool) -> None:
    if data:
        online_to_df = {'online': True,
                        'timestamp': str(datetime.now())}
    else:
        online_to_df = {'online': False,
                        'timestamp': str(datetime.now())}
    online_to_df = pd.DataFrame(data=online_to_df, index=[0])
    roverdata.online = pd.concat([roverdata.online, online_to_df], ignore_index=True)
    
def add_obstacles_to_df(data: str) -> None:
    try: 
        data_list = data.split(',')
        del data_list[-1]
        del data_list[0]
        if len(data_list) == 1:
            if appcfg.obstacles_amount == 0: #Synchronize to sunray fw
                current_map.obstacles = pd.DataFrame() 
                return
        obstacles_number = int(data_list[0]) 
        del data_list[0]
        data_list = [float(x) if '.' in x else int(x) for x in data_list]
        for i in range(obstacles_number):
            obstacle = create_obstacle(data_list[3:4+2*data_list[3]])
            if current_map.obstacles.empty or current_map.obstacles[current_map.obstacles['CRC'] == obstacle['CRC'].unique()[0]].empty:
                current_map.obstacles = pd.concat([current_map.obstacles, obstacle], ignore_index=True)
            del data_list[0:4+2*data_list[3]]
        #check of max amount of obstacles
        if appcfg.obstacles_amount != 0:
            if not current_map.obstacles.empty and len(current_map.obstacles['CRC'].unique()) > appcfg.obstacles_amount:
                obstacles_crc = current_map.obstacles['CRC'].unique()
                obstacles_crc = obstacles_crc[-appcfg.obstacles_amount:]
                current_map.obstacles = current_map.obstacles[current_map.obstacles['CRC'].isin(obstacles_crc)]
                current_map.obstacles = current_map.obstacles.reset_index(drop=True)
    except Exception as e:
        logger.error('Backend: Failed to write obstacles data to data frame')
        logger.debug(str(e))
