import logging
logger = logging.getLogger(__name__)
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
import os

from . import roverdata
from .mapdata import current_map, mapping_maps

#import roverdata, mapdata


def read(absolute_path) -> None:
    #cwd = Path.cwd()
    
    #Try to read State Date from file
    try:
        with open(absolute_path.replace('/src/backend', '/src/data/datacfg.json')) as f: 
            path_to_data = json.load(f)
            f.close()
        path_to_state_data = path_to_data['path'][1]['measure'][0]['state']
        roverdata.state = pd.read_pickle(absolute_path.replace('/src/backend', path_to_state_data))
        if not 'lateral_error' in roverdata.state.columns:
            roverdata.state['lateral_error'] = 0
        logger.info('Backend: State data are loaded successfully')
    except:
        logger.warning('Backend: Failed to load state data, create a default data frame')
        state = {"battery_voltage":{"0":0},
                 "position_x":{"0":0},
                 "position_y":{"0":0},
                 "position_delta":{"0":0},
                 "position_solution":{"0":0},
                 "job":{"0":10},
                 "position_mow_point_index":{"0":0},
                 "position_age":{"0":0},
                 "sensor":{"0":0},
                 "target_x":{"0":0},
                 "target_y":{"0":0},
                 "position_accuracy":{"0":0},
                 "position_visible_satellites":{"0":0},
                 "amps":{"0":0},
                 "position_visible_satellites_dgps":{"0":0},
                 "map_crc":{"0":0},
                 "lateral_error": {"0":0},
                 "timestamp":{"0":str(datetime.now())}}
        roverdata.state = pd.DataFrame(data=state)
        #calceddata.calcdata_from_state()

    #Try to read Stats Data from file
    try:
        path_to_stats_data = path_to_data['path'][1]['measure'][1]['stats']
        roverdata.stats = pd.read_pickle(absolute_path.replace('/src/backend', path_to_stats_data))
        if not 'duration_mow_motor_recovery' in roverdata.stats:
            roverdata.stats['duration_mow_motor_recovery'] = 0
        logger.info('Backend: Statistics data are loaded successfully')
    except:
        logger.warning('Backend: Failed to load statistics data, create a default data frame')
        stats = {"duration_idle":{"0":0},
                 "duration_charge":{"0":0},
                 "duration_mow":{"0":0},
                 "duration_mow_invalid":{"0":0},
                 "duration_mow_float":{"0":0},
                 "duration_mow_fix":{"0":0},
                 "distance_mow_traveled":{"0":0},
                 "counter_gps_chk_sum_errors":{"0":0},
                 "counter_dgps_chk_sum_errors":{"0":0},
                 "counter_invalid_recoveries":{"0":0},
                 "counter_float_recoveries":{"0":0},
                 "counter_gps_jumps":{"0":0},
                 "counter_gps_motion_timeout":{"0":0},
                 "counter_imu_triggered":{"0":0},
                 "counter_sonar_triggered":{"0":0},
                 "counter_bumper_triggered":{"0":0},
                 "counter_obstacles":{"0":0},
                 "time_max_cycle":{"0":0},
                 "time_max_dpgs_age":{"0":0},
                 "serial_buffer_size":{"0":0},
                 "free_memory":{"0":0},
                 "reset_cause":{"0":0},
                 "temp_min":{"0":0},
                 "temp_max":{"0":0},
                 "duration_mow_motor_recovery":{"0":0},
                 "timestamp":{"0":str(datetime.now())}}
        roverdata.stats = pd.DataFrame(data=stats)

    #Try to read Calced from State Data from file
    try:
        path_to_calced_from_state_data = path_to_data['path'][1]['measure'][3]['calcedstate']
        roverdata.calced_from_state = pd.read_pickle(absolute_path.replace('/src/backend', path_to_calced_from_state_data))
        logger.info('Backend: Calced data from state are loaded successfully')
    except:
        logger.warning('Backend: Failed to load calced data from state, create a default data frame')
        calced_from_state = {"solution":{"0":"invalid"},
                             "job":{"0":"unknown"},
                             "sensor":{"0":"unknown"},
                             "soc":{"0":0},
                             "timestamp":{"0":str(datetime.now())}}
        roverdata.calced_from_state = pd.DataFrame(data=calced_from_state)
    
    #Try to read Calced from Stats Data from file
    try:
        path_to_calced_from_stats_data = path_to_data['path'][1]['measure'][4]['calcedstats']
        roverdata.calced_from_stats = pd.read_pickle(absolute_path.replace('/src/backend', path_to_calced_from_stats_data))
        logger.info('Backend: Calced data from stats are loaded successfully')
    except:
        logger.warning('Backend: Failed to load calced data from stats, create a default data frame')
        calced_from_stats = {"duration_idle":{"0":0},
                            "duration_charge":{"0":0},
                            "duration_mow":{"0":0},
                            "duration_mow_invalid":{"0":0},
                            "duration_mow_float":{"0":0},
                            "duration_mow_fix":{"0":0},
                            "distance_mow_traveled":{"0":0},
                            "counter_gps_chk_sum_errors":{"0":0},
                            "counter_dgps_chk_sum_errors":{"0":0},
                            "counter_invalid_recoveries":{"0":0},
                            "counter_float_recoveries":{"0":0},
                            "counter_gps_jumps":{"0":0},
                            "counter_gps_motion_timeout":{"0":0},
                            "counter_imu_triggered":{"0":0},
                            "counter_sonar_triggered":{"0":0},
                            "counter_bumper_triggered":{"0":0},
                            "counter_obstacles":{"0":0},
                            "time_max_cycle":{"0":0},
                            "time_max_dpgs_age":{"0":0},
                            "serial_buffer_size":{"0":0},
                            "free_memory":{"0":0},
                            "reset_cause":{"0":0},
                            "temp_min":{"0":0},
                            "temp_max":{"0":0},
                            "timestamp":{"0":str(datetime.now())}}
        roverdata.calced_from_stats = pd.DataFrame(data=calced_from_stats)

def read_perimeter() -> None:
    absolute_path = os.path.dirname(__file__)
    try:
        current_map.name = current_map.read_map_name()
    except Exception as e:
        logger.warning('Backend: Could not read perimeter name from tmp.json')
        logger.debug(str(e))
        current_map.name = ''
    if current_map.name == '':
        logger.warning('Backend: Selected perimeter name is an empty string. Please upload or create a new perimeter')
        return
    try:
        with open(absolute_path.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
            path_to_data = json.load(f)
            f.close()
    except Exception as e:
        logger.error('Backend: Could not save data to the file. Missing datacfg.json')
        logger.debug(str(e))
        return
    try:
        path_to_map_data = path_to_data['path'][2]['map'][0]['perimeter']
        mapping_maps.saved = pd.read_json(absolute_path.replace('/src/backend/data', path_to_map_data))
        logger.info('Backend: Saved perimeters are loaded successfully')
    except Exception as e:
        logger.warning('Backend: Failed to load saved perimeters from file')
        logger.debug(str(e))
        return
    try:
        current_map.perimeter = mapping_maps.saved[mapping_maps.saved['name'] == current_map.name]
        current_map.perimeter = current_map.perimeter.reset_index(drop=True)
        current_map.create(current_map.name)
        logger.info('Backend: Selected perimeter: '+current_map.name)
    except Exception as e:
        logger.error('Backend: Loading saved perimeter failed')
        logger.debug(str(e))

def save(name: str()) -> None:
    absolute_path = os.path.dirname(__file__)
    #cwd = Path.cwd()
    try:
        with open(absolute_path.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
            path_to_data = json.load(f)
            f.close()
    except Exception as e:
        logger.error('Backend: Could not save data to the file. Missing datacfg.json')
        logger.debug(str(e))
        return
    if name == 'state':
        try:
            path_to_state_data = path_to_data['path'][1]['measure'][0]['state']
            roverdata.state.to_pickle(absolute_path.replace('/src/backend/data', path_to_state_data))
            logger.info('Backend: State data are saved successfully in state.pickle')
            path_to_calcstate_data = path_to_data['path'][1]['measure'][3]['calcedstate']
            roverdata.calced_from_state.to_pickle(absolute_path.replace('/src/backend/data', path_to_calcstate_data))
            logger.info('Backend: Calced state data are saved successfully in calcstate.pickle')
        except Exception as e:
            logger.error('Backend: Could not save state data to the file')
            logger.debug(str(e))
    elif name == 'stats':
        try:
            path_to_stats_data = path_to_data['path'][1]['measure'][1]['stats']
            roverdata.stats.to_pickle(absolute_path.replace('/src/backend/data', path_to_stats_data))
            logger.info('Backend: Statistics data are saved successfully in stats.pickle')
            path_to_calcstats_data = path_to_data['path'][1]['measure'][4]['calcedstats']
            roverdata.calced_from_stats.to_pickle(absolute_path.replace('/src/backend/data', path_to_calcstats_data))
            logger.info('Backend: Calced statistics data are saved successfully in calcstats.pickle')
        except Exception as e:
            logger.error('Backend: Could not save statistics data to the file')
            logger.debug(str(e))

def save_perimeter(perimeter_arr: pd.DataFrame, perimeter: pd.DataFrame, perimeter_name: str()) -> None:
    absolute_path = os.path.dirname(__file__)
    try:
        with open(absolute_path.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
            path_to_data = json.load(f)
            f.close()
    except Exception as e:
        logger.error('Backend: Could not save data to the file. Missing datacfg.json')
        logger.debug(str(e))
        return
    try:
        perimeter['name'] = perimeter_name
        perimeter_arr = pd.concat([perimeter_arr, perimeter], ignore_index=True)
        perimeter_arr.to_json(absolute_path.replace('/src/backend/data', path_to_data['path'][2]['map'][0]['perimeter']), date_format='iso')
        logger.info('Backend: Perimeter data are successfully saved in perimeter.json')
        mapping_maps.saved = perimeter_arr
    except:
        logger.warning('Backend: Could not save perimeter data to the file')

if __name__ == '__main__':
    read()