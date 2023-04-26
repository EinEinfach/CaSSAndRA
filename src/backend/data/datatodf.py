import logging
logger = logging.getLogger(__name__)

#packege imports
import pandas as pd
from datetime import datetime

#local imports
from . import roverdata, calceddata

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
                    'timestamp': str(datetime.now())}
        state_to_df = pd.DataFrame(data=state_to_df, index=[0])
        roverdata.state = pd.concat([roverdata.state, state_to_df], ignore_index=True)
        calceddata.calcdata_from_state()
    except:
        logger.warning('Backend: Received state message is not valid and will be ignored')
    

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
                    'timestamp': str(datetime.now())}
        stats_to_df = pd.DataFrame(data=stats_to_df, index=[0])
        roverdata.stats = pd.concat([roverdata.stats, stats_to_df], ignore_index=True)
        calceddata.calcdata_from_stats()
    except:
        logger.warning('Backend: Received stats message is not valid and will be ignored')

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
    data_list = data.split(',')
    del data_list[-1]
    del data_list[-1]
    del data_list[0]
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
                        'timestamp']
    roverdata.state = pd.concat([roverdata.state, state_to_df], ignore_index=True)
    calceddata.calcdata_from_state()

def add_stats_to_df(data: str()) -> None:
    data_list = data.split(',')
    del data_list[-1]
    del data_list[0]
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
                            'timestamp'
                           ]
    roverdata.stats = pd.concat([roverdata.stats, stats_to_df], ignore_index=True)
    calceddata.calcdata_from_stats()

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
