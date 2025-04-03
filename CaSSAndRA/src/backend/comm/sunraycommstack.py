import logging
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
from datetime import datetime

from ..data.mapdata import current_map
from ..data.roverdata import robot
from ..data.cfgdata import rovercfg, commcfg
from . import cmdlist
#from . api import cassandra_api

def takemap(perimeter: pd.DataFrame, way: pd.DataFrame, dock: bool) -> pd.DataFrame:
    perimeter = perimeter[perimeter['type'] != 'search wire']
    logger.info('Backend: Prepare map and way data for transmition')

    #Remove dockpoints, if neccessary (e.g. for goto command)
    if not dock:
        perimeter = perimeter[perimeter['type'] != 'dockpoints']

    data = pd.concat([perimeter, way], ignore_index=True)
    
    data = data.round(2)
    #Create AT+W messages
    amount_of_packages = data.index//30
    data['package_nr'] = amount_of_packages
    data['coords'] = ','+data['X'].astype(str)+','+data['Y'].astype(str) 
    data = data.groupby('package_nr').agg({'coords': lambda x: list(x)})
    buffer = pd.DataFrame()
    for i, row in data.iterrows():
        buffer_str = ''.join(row['coords'])
        msg = {'msg': 'AT+W,'+str(i*30)+buffer_str}
        msg_df = pd.DataFrame([msg])
        buffer = pd.concat([buffer, msg_df], ignore_index=True)
        logger.debug('Add to takemap buffer: '+str(msg))

    #Create AT+N message
    perimeter_cnt = len(perimeter[perimeter['type'] == 'perimeter'])
    exclusion_names = perimeter['type'].unique()
    exclusion_names = np.delete(exclusion_names, np.where(exclusion_names == 'perimeter'))
    exclusion_names = np.delete(exclusion_names, np.where(exclusion_names == 'dockpoints'))
    exclusions_cnt = len(perimeter[perimeter['type'].isin(exclusion_names)])
    docking_cnt = len(perimeter[perimeter['type'] == 'dockpoints'])
    if way.empty:
        way_cnt = 0
    else:
        way_cnt = len(way[way['type'] == 'way'])
    msg = {'msg': 'AT+N,'+str(perimeter_cnt)+','+str(exclusions_cnt)+','+str(docking_cnt)+','+str(way_cnt)+',0'}
    msg_df = pd.DataFrame([msg])
    buffer = pd.concat([buffer, msg_df], ignore_index=True)

    #Create AT+X message
    exclusion_pts = []
    for exclusion in exclusion_names:
        exclusion_pts.append(len(perimeter[perimeter['type'] == exclusion]))
    exclusion_pts = str(exclusion_pts)
    exclusion_pts = exclusion_pts.replace('[', '')
    exclusion_pts = exclusion_pts.replace(']', '')
    exclusion_pts = exclusion_pts.replace(' ', '')
    msg = {'msg': 'AT+X,0,'+exclusion_pts}
    msg_df = pd.DataFrame([msg])
    buffer = pd.concat([buffer, msg_df], ignore_index=True)

    return buffer

def move(movement: list) -> pd.DataFrame:
    if movement[0] !=0 or movement[1] != 0:
        msg = {'msg': 'AT+M,'+str(movement[0])+','+str(movement[1])}
        buffer = pd.DataFrame([msg])
        logger.debug(f'Backend: Command "MOVE" is prepared. X:{movement[0]} Y:{movement[1]}')
        return buffer
    elif movement[0] == 0 and movement[1] == 0:
        msg = {'msg': 'AT+M,0.0,0.0'}
        buffer = pd.DataFrame([msg])
        logger.debug(f'Backend: Command "MOVE" is prepared. X:{movement[0]} Y:{movement[1]}')
        cmdlist.cmd_move = False
        return buffer

def goto() -> pd.DataFrame:
    msg = {'msg': 'AT+C,0,1,'+str(rovercfg.gotospeed_setpoint)+','+str(rovercfg.fix_timeout)+',0,-1,-1,-1,-1,-1,0'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command goto is prepared')
    cmdlist.cmd_goto = False
    return buffer

def stop():
    robot.status_tmp_timestamp = datetime.now()
    robot.set_robot_status('stop', 'stop')

    msg = {'msg': 'AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command stop is prepared')
    cmdlist.cmd_stop = False
    return buffer

def dock() -> pd.DataFrame:
    msg = {'msg': 'AT+C,0,4,-1,-1,-1,-1,-1,-1,-1,-1,-1'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command dock is prepared')
    cmdlist.cmd_dock = False
    return buffer

def mow() -> pd.DataFrame:
    msg = {'msg': 'AT+C,1,1,'+str(rovercfg.mowspeed_setpoint)+','+str(rovercfg.fix_timeout)+','+str(int(rovercfg.finish_and_restart))+',-1,-1,-1,-1,-1,1'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command start is prepared')
    cmdlist.cmd_mow = False
    return buffer

def resume() -> pd.DataFrame:
    buffer = robot.last_cmd
    logger.debug('Backend: Command resume is prepared')
    cmdlist.cmd_resume = False
    return buffer

def shutdown() -> pd.DataFrame:
    msg = {'msg': 'AT+Y3'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command shutdown is preapred')
    cmdlist.cmd_shutdown = False
    return buffer

def reboot() -> pd.DataFrame:
    msg = {'msg': 'AT+Y'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command reboot is prepared')
    cmdlist.cmd_reboot = False
    return buffer

def gpsreboot() -> pd.DataFrame:
    msg = {'msg': 'AT+Y2'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command GPS reboot is prepared')
    cmdlist.cmd_gps_reboot = False
    return buffer

def togglemowmotor() -> pd.DataFrame:
    #mow motor switch on
    if not robot.last_mow_status:
        msg = {'msg': 'AT+C,1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1'}
        cmdlist.cmd_toggle_mow_motor = False
    #mow motor switch off
    else:
        msg = {'msg': 'AT+C,0,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1'}
        cmdlist.cmd_toggle_mow_motor = False
    buffer = pd.DataFrame([msg])
    return buffer

def takepositionmode() -> pd.DataFrame:
    positionmode = rovercfg.positionmode
    if positionmode == 'absolute':
        positionmode = '1,'
    else:
        positionmode = '0,'
    msg = {'msg': 'AT+P,'+positionmode+str(rovercfg.lon)+','+str(rovercfg.lat)}
    buffer = pd.DataFrame([msg])
    cmdlist.cmd_set_positionmode = False
    return buffer

def changespeed(new_speed: float) -> pd.DataFrame:
    msg = {'msg': 'AT+C,-1,-1,'+str(new_speed)+',-1,-1,-1,-1,-1,-1,-1,-1'}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Command change speed is prepared, new value is: '+str(new_speed))
    cmdlist.cmd_changemowspeed = False
    cmdlist.cmd_changegotospeed = False
    return buffer

def skipnextpoint() -> pd.DataFrame:
    msg = {'msg': 'AT+C,-1,-1,-1,-1,-1,-1,1,-1,-1,-1,-1'}
    buffer = pd.DataFrame([msg])
    logger.debug('Command skip next point is prepared')
    cmdlist.cmd_skipnextpoint = False
    return buffer

def custom() -> pd.DataFrame:
    msg = {'msg': cmdlist.cmd_custom_str}
    buffer = pd.DataFrame([msg])
    logger.debug('Backend: Custom command is prepared')
    cmdlist.cmd_custom = False
    cmdlist.cmd_custom_str = ''
    return buffer

def skiptomowprogress(progress: float) -> pd.DataFrame:
    msg = {'msg': 'AT+C,-1,-1,-1,-1,-1,'+str(progress)+',-1,-1,-1,-1,-1'}
    buffer = pd.DataFrame([msg])
    logger.debug('Command skip to progress is prepared')
    cmdlist.cmd_skiptomowprogress = False
    return buffer

def ononlinemessage(data: str) -> pd.DataFrame:
    try: 
        if 'true' in data:
            online = {'online': True, 'timestamp': str(datetime.now())}
        else:
            online = {'online': False, 'timestamp': str(datetime.now())}
        online_df = pd.DataFrame(data=online, index=[0])
        return online_df
    except Exception as e:
        logger.error('Could not decode online message')
        logger.error(str(e))
        return pd.DataFrame()

def onpropsmessage(data: str) -> pd.DataFrame:
    try:
        props = {'firmware': [data[1]], 
                 'version': [data[2]], 
                 'timestamp': str(datetime.now())
                 }
        props_df = pd.DataFrame(props)
        return props_df
    except Exception as e:
        logger.error('Could not decode props string')
        logger.error(str(e))
        return pd.DataFrame()

def onpropsmqttmessage(data: dict) -> pd.DataFrame:
    try: 
        props = {'firmware':data['firmware'],
                    'version':data['version'],
                    'timestamp': str(datetime.now())
                    }
        props_df = pd.DataFrame(data=props, index=[0])
        return props_df
    except Exception as e:
        logger.error('Could not decode props string')
        logger.error(str(e))
        return pd.DataFrame()

def onstatemessage(data: str) -> pd.DataFrame:
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
        state_df = pd.DataFrame([data_list])
        state_df.columns = ['battery_voltage',
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
        return state_df
    except Exception as e:
        logger.error('Could not decode received state string')
        logger.error(str(e))
        return pd.DataFrame()

def onstatemqttmessage(data: dict) -> pd.DataFrame:
    try: 
        state = {'battery_voltage':data['battery_voltage'],
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
        state_df = pd.DataFrame(data=state, index=[0])
        return state_df
    except Exception as e:
        logger.error('Could not decode received state string')
        logger.error(str(e))
        return pd.DataFrame()

def onstatsmessage(data: str) -> pd.DataFrame:
    try: 
        data_list = data.split(',')
        del data_list[-1]
        del data_list[0]
        #handle old AT+T strings (older then 1.0.3XX)
        if len(data_list) < 25:
            data_list.append('0')
        #handle old AT+T strings (older then 1.0.321)
        if len(data_list) < 31:
            data_list.extend(['0', '0', '0', '0', '0', '0'])
        data_list = [float(x) if '.' in x else int(x) for x in data_list]
        data_list.append(str(datetime.now()))
        stats_df = pd.DataFrame([data_list])
        stats_df.columns = [
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
                                'counter_lift_triggered',
                                'counter_gps_no_speed_triggered',
                                'counter_tof_triggered',
                                'counter_diff_imu_wheel_yaw_speed_triggered',
                                'counter_imu_no_rotation_triggered',
                                'counter_rotation_timeout_triggered',
                                'timestamp'
                            ]
        return stats_df
    except Exception as e:
        logger.error('Could not decode received stats string')
        logger.error(str(e))
        return pd.DataFrame()

def onstatsmqttmessage(data: dict) -> pd.DataFrame:
    try: 
        stats = {'duration_idle':data['duration_idle'],
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
                    'counter_lift_triggered': 0,
                    'counter_gps_no_speed_triggered': 0,
                    'counter_tof_triggered': 0,
                    'counter_diff_imu_wheel_yaw_speed_triggered': 0,
                    'counter_imu_no_rotation_triggered': 0,
                    'counter_rotation_timeout_triggered': 0,
                    'timestamp': str(datetime.now())}
        stats_df = pd.DataFrame(data=stats, index=[0])
        return stats_df
    except Exception as e:
        logger.error('Could not decode received stats string')
        logger.error(str(e))
        return pd.DataFrame()

def create_obstacle(data: list) -> pd.DataFrame:
    list_for_df = []
    number_of_points = data[0]
    del data[0]
    for i in range(number_of_points):
        list_for_df.append([data[2*i], data[2*i+1]])
    list_for_df.append([data[0], data[1]])
    obstacle_df = pd.DataFrame(list_for_df)
    obstacle_df.columns = ['X', 'Y']
    obstacle_df['type'] = 'points'
    obstacleCRCx = obstacle_df['X']*100 
    obstacleCRCy = obstacle_df['Y']*100 
    obstacle_CRC = int(obstacleCRCx.sum() + obstacleCRCy.sum())
    obstacle_df['CRC'] = obstacle_CRC
    return obstacle_df

def onobstaclemessage(data: str) -> pd.DataFrame:
    try: 
        obstacles = pd.DataFrame()
        data_list = data.split(',')
        del data_list[-1]
        del data_list[0]
        obstacles_amount = int(data_list[0]) 
        del data_list[0]
        data_list = [float(x) if '.' in x else int(x) for x in data_list]
        for i in range(obstacles_amount):
            obstacle = create_obstacle(data_list[3:4+2*data_list[3]])
            obstacles = pd.concat([obstacles, obstacle], ignore_index=True)
            del data_list[0:4+2*data_list[3]]
        return obstacles
    except Exception as e:
        logger.error('Could not decode received obstacle string')
        logger.error(str(e))
        return pd.DataFrame()