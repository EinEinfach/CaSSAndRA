import logging
logger = logging.getLogger(__name__)
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
import os

from . import roverdata
from .mapdata import current_map, mapping_maps, current_task, tasks

file_paths = None

def read(measure_file_paths) -> None:
    #Try to read State Date from file
    try:
        roverdata.state = pd.read_pickle(measure_file_paths.state)
        if not 'lateral_error' in roverdata.state.columns:
            roverdata.state['lateral_error'] = 0
        if not 'timetable_autostartstop_dayofweek' in roverdata.state.columns:
            roverdata.state['timetable_autostartstop_dayofweek'] = 0
            roverdata.state['timetabel_autostartstop_hour'] = 0
        logger.info('Backend: State data are loaded successfully')
        if roverdata.state.empty:
            logger.warning('state.pickle is empty, create a default data frame')
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
                 "timetable_autostartstop_dayofweek":{"0":0},
                 "timetabel_autostartstop_hour":{"0":0}, 
                 "timestamp":{"0":str(datetime.now())}}
            roverdata.state = pd.DataFrame(data=state)
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
                 "timetable_autostartstop_dayofweek":{"0":0},
                 "timetabel_autostartstop_hour":{"0":0}, 
                 "timestamp":{"0":str(datetime.now())}}
        roverdata.state = pd.DataFrame(data=state)
        #calceddata.calcdata_from_state()

    #Try to read Stats Data from file
    try:
        roverdata.stats = pd.read_pickle(measure_file_paths.stats)
        if not 'duration_mow_motor_recovery' in roverdata.stats:
            roverdata.stats['duration_mow_motor_recovery'] = 0
        logger.info('Backend: Statistics data are loaded successfully')
        if roverdata.stats.empty:
            logger.warning('stats.pickle is empty, create a default data frame')
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
        roverdata.calced_from_state = pd.read_pickle(measure_file_paths.calcedstate)
        logger.info('Backend: Calced data from state are loaded successfully')
        if roverdata.calced_from_state.empty:
            logger.warning('calcedstate.pickle is empty, create a default data frame')
            calced_from_state = {"solution":{"0":"invalid"},
                             "job":{"0":"unknown"},
                             "sensor":{"0":"unknown"},
                             "soc":{"0":0},
                             "timestamp":{"0":str(datetime.now())}}
            roverdata.calced_from_state = pd.DataFrame(data=calced_from_state)
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
        roverdata.calced_from_stats = pd.read_pickle(measure_file_paths.calcedstats)
        logger.info('Backend: Calced data from stats are loaded successfully')
        if roverdata.calced_from_stats.empty:
            logger.warning('calcedstats.pickle is empty, create a default data frame')
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

def read_perimeter(map_file_paths) -> None:
    try:
        # todo: refactor this class so we initialize with correct values before using it
        #       currently this class is being created before backend has fully initialized
        #       so we are having to set the tmp.json file path here
        current_map.current_perimeter_file = map_file_paths.tmp
        current_map.name = current_map.read_map_name()
    except Exception as e:
        logger.warning('Backend: Could not read perimeter name from tmp.json')
        logger.debug(str(e))
        current_map.name = ''

    try:
        mapping_maps.saved = pd.read_json(map_file_paths.perimeter)
        logger.info('Backend: Saved perimeters are loaded successfully')
    except Exception as e:
        logger.warning('Backend: Failed to load saved perimeters from file')
        logger.debug(str(e))
        return
    try:
        if mapping_maps.saved.empty:
            logger.info('Backend: perimeter.json contains no map data')
            return
        if current_map.name == '':
            logger.info('Backend: No perimeter selected, go ahead without selection')
            return
        current_map.perimeter = mapping_maps.saved[mapping_maps.saved['name'] == current_map.name]
        current_map.perimeter = current_map.perimeter.reset_index(drop=True)
        current_map.create(current_map.name)
        current_task.create()
        logger.info('Backend: Selected perimeter: '+current_map.name)
    except Exception as e:
        logger.error('Backend: Loading saved perimeter failed')
        logger.debug(str(e))

def save(name: str, file_paths) -> None:
    if name == 'state':
        try:
            roverdata.state.to_pickle(file_paths.measure.state)
            logger.info('Backend: State data are saved successfully in state.pickle')

            roverdata.calced_from_state.to_pickle(file_paths.measure.calcedstate)
            logger.info('Backend: Calced state data are saved successfully in calcstate.pickle')
        except Exception as e:
            logger.error('Backend: Could not save state data to the file')
            logger.debug(str(e))
    elif name == 'stats':
        try:
            roverdata.stats.to_pickle(file_paths.measure.stats)
            logger.info('Backend: Statistics data are saved successfully in stats.pickle')

            roverdata.calced_from_stats.to_pickle(file_paths.measure.calcedstats)
            logger.info('Backend: Calced statistics data are saved successfully in calcstats.pickle')
        except Exception as e:
            logger.error('Backend: Could not save statistics data to the file')
            logger.debug(str(e))

def save_perimeter(perimeter_arr: pd.DataFrame, perimeter: pd.DataFrame, perimeter_name: str) -> None:
    if perimeter_name is None:
        logger.info('Backend: Could not save perimeter. Perimeter name is not valid')
    elif perimeter_arr.empty or not (perimeter_name in perimeter_arr['name'].unique()):
        try:
            perimeter['name'] = perimeter_name
            perimeter_arr = pd.concat([perimeter_arr, perimeter], ignore_index=True)
            perimeter_arr.to_json(file_paths.map.perimeter, indent=2, date_format='iso')
            logger.info('Backend: Perimeter data are successfully saved in perimeter.json')
            mapping_maps.saved = perimeter_arr
            #check for tasks what have to be copied
            if mapping_maps.map_old_name != None:
                map_tasks = tasks.saved[tasks.saved['map name'] == mapping_maps.map_old_name]
                map_tasks_parameters = tasks.saved_parameters[tasks.saved_parameters['map name'] == mapping_maps.map_old_name]
                map_tasks.loc[:, 'map name'] = perimeter_name
                map_tasks_parameters.loc[:, 'map name'] = perimeter_name
                tasks.saved = pd.concat([tasks.saved, map_tasks], ignore_index=True)
                tasks.saved_parameters = pd.concat([tasks.saved_parameters, map_tasks_parameters], ignore_index=True)
                tasks.saved.to_json(file_paths.map.tasks, indent=2, date_format='iso')
                logger.info('Task data are successfully saved in tasks.json')
                tasks.saved_parameters.to_json(file_paths.map.tasks_parameters, indent=2, date_format='iso')
                logger.info('Tasks parameters data are successfully saved in tasks_parameters.json')
        except Exception as e:
            logger.warning('Backend: Could not save perimeter data to the file')
            logger.debug(str(e))
    else:
        logger.info('Backend: Could not save perimeter. Perimeter name is already exsist.')

def remove_perimeter(perimeter_arr: pd.DataFrame, perimeter_name: str, tasks_arr: pd.DataFrame, tasks_parameters_arr) -> None:
    try:
        perimeter_arr = perimeter_arr[perimeter_arr['name'] != perimeter_name]
        perimeter_arr.to_json(file_paths.map.perimeter, indent=2, date_format='iso')
        #remove also tasks belong to this map
        remove_task(tasks_arr, tasks_parameters_arr, [''], perimeter_name)
        logger.info('Backend: Perimeter is successfully removed from perimeter.json')
        mapping_maps.saved = perimeter_arr
        mapping_maps.select_saved(pd.DataFrame(columns=['X', 'Y', 'type', 'name']))
    except Exception as e:
        logger.error('Backend: Could not remove perimeter data from file')
        logger.debug(str(e))

def copy_perimeter(perimeter_arr: pd.DataFrame, perimeter_name: str, cpy_perimeter_name: str) -> None:
    if cpy_perimeter_name is None:
        logger.info('Could not copy perimeter. Perimeter name is not valid')
    elif not cpy_perimeter_name in perimeter_arr['name'].unique():
        try:
            perimeter = perimeter_arr[perimeter_arr['name'] == perimeter_name]
            perimeter['name'] = cpy_perimeter_name
            perimeter_arr = pd.concat([perimeter_arr, perimeter], ignore_index=True)
            perimeter_arr.to_json(file_paths.map.perimeter, indent=2, date_format='iso')
            logger.info('Perimeter data are successfully saved in perimeter.json')
            mapping_maps.saved = perimeter_arr
            map_tasks = tasks.saved[tasks.saved['map name'] == perimeter_name]
            map_tasks_parameters = tasks.saved_parameters[tasks.saved_parameters['map name'] == perimeter_name]
            map_tasks.loc[:, 'map name'] = cpy_perimeter_name
            map_tasks_parameters.loc[:, 'map name'] = cpy_perimeter_name
            tasks.saved = pd.concat([tasks.saved, map_tasks], ignore_index=True)
            tasks.saved_parameters = pd.concat([tasks.saved_parameters, map_tasks_parameters], ignore_index=True)
            tasks.saved.to_json(file_paths.map.tasks, indent=2, date_format='iso')
            logger.info('Task data are successfully saved in tasks.json')
            tasks.saved_parameters.to_json(file_paths.map.tasks_parameters, indent=2, date_format='iso')
            logger.info('Tasks parameters data are successfully saved in tasks_parameters.json')
        except Exception as e:
            logger.warning('Could not save perimeter data to the file')
            logger.debug(str(e))
    else:
        logger.info('Could not copy perimeter. Perimeter name is already exsist.')

def rename_perimeter(perimeter_name: str, new_perimeter_name: str) -> None:
    if new_perimeter_name is None:
        logger.info('Could not rename perimeter. Perimeter name is not valid')
    elif not new_perimeter_name in mapping_maps.saved['name'].unique():
        try:
            perimeter = mapping_maps.saved[mapping_maps.saved['name'] == perimeter_name]
            perimeters = mapping_maps.saved[mapping_maps.saved['name'] != perimeter_name]
            perimeter.loc[:, 'name'] = new_perimeter_name
            mapping_maps.saved = pd.concat([perimeters, perimeter], ignore_index=True)
            mapping_maps.saved.to_json(file_paths.map.perimeter, indent=2, date_format='iso')
            logger.info('Perimeter data are successfully saved in perimeter.json')
            map_tasks = tasks.saved[tasks.saved['map name'] == perimeter_name]
            other_tasks = tasks.saved[tasks.saved['map name'] != perimeter_name]
            map_tasks_parameters = tasks.saved_parameters[tasks.saved_parameters['map name'] == perimeter_name]
            other_tasks_parameters = tasks.saved_parameters[tasks.saved_parameters['map name'] != perimeter_name]
            map_tasks.loc[:, 'map name'] = new_perimeter_name
            map_tasks_parameters.loc[:, 'map name'] = new_perimeter_name
            tasks.saved = pd.concat([other_tasks, map_tasks], ignore_index=True)
            tasks.saved_parameters = pd.concat([other_tasks_parameters, map_tasks_parameters], ignore_index=True)
            tasks.saved.to_json(file_paths.map.tasks, indent=2, date_format='iso')
            logger.info('Backend: Task data are successfully saved in tasks.json')
            tasks.saved_parameters.to_json(file_paths.map.tasks_parameters, indent=2, date_format='iso')
            logger.info('Backend: Tasks parameters data are successfully saved in tasks_parameters.json')
            #remove also perimeter in current map, if matched
            if perimeter_name == current_map.name:
                current_map.clear_map()
        except Exception as e:
            logger.warning('Could not save perimeter data to the file')
            logger.debug(str(e))
    else:
        logger.info('Could not rename perimeter. Perimeter name is already exsist.')

def save_task(task_arr: pd.DataFrame, task_parameter_arr: pd.DataFrame, task: pd.DataFrame, task_parameters: pd.DataFrame, task_name: str) -> None:
    if task_name is None:
        logger.info('Backend: Could not save task. Task name is not valid')
        return
    if not task_arr.empty:
        task_names_to_check = task_arr[task_arr['map name'] == current_map.name]
    if task_arr.empty or not (task_name in task_names_to_check['name'].unique()):
        try:
            task['name'] = task_name
            task_arr = pd.concat([task_arr, task], ignore_index=True)
            task_arr.to_json(file_paths.map.tasks, indent=2, date_format='iso')
            logger.info('Backend: Task data are successfully saved in tasks.json')
            tasks.saved = task_arr
            task_parameters['name'] = task_name
            task_parameter_arr = pd.concat([task_parameter_arr, task_parameters], ignore_index=True)
            task_parameter_arr.to_json(file_paths.map.tasks_parameters, indent=2, date_format='iso')
            logger.info('Backend: Tasks parameters data are successfully saved in tasks_parameters.json')
            tasks.saved_parameters = task_parameter_arr
        except Exception as e:
            logger.warning('Backend: Could not save task data to the file')
            logger.debug(str(e))
    else:
        logger.info('Backend: Could not save task. Task name is already exsist.')    

def read_tasks(map_file_paths) -> None:
    try:
        tasks.saved = pd.read_json(map_file_paths.tasks)
        logger.info('Backend: Saved tasks are loaded successfully')
        tasks.saved_parameters = pd.read_json(map_file_paths.tasks_parameters)
        logger.info('Backend: Saved tasks parameters are loaded successfully')
    except Exception as e:
        logger.info('Backend: Failed to load saved tasks from file')
        logger.debug(str(e))
        return

def remove_task(task_arr: pd.DataFrame, task_parameter_arr: pd.DataFrame, task_name: list, map_name: str) -> None:
    try:
        if task_name[0] == '':
            task_arr = task_arr[task_arr['map name'] != map_name]
            task_arr.to_json(file_paths.map.tasks, indent=2, date_format='iso')
            logger.info('Backend: Tasks are successfully removed from tasks.json')
            task_parameter_arr = task_parameter_arr[task_parameter_arr['map name'] != map_name]
            task_parameter_arr.to_json(file_paths.map.tasks_parameters, indent=2, date_format='iso')
            logger.info('Backend: Tasks parameters are successfully removed from tasks_parameters.json')
        else:
            task_arr = task_arr[(task_arr['name'] != task_name[0]) & (task_arr['map name'] == map_name) | (task_arr['map name'] != map_name)]
            task_arr.to_json(file_paths.map.tasks, indent=2, date_format='iso')
            logger.info('Backend: Task is successfully removed from tasks.json')
            task_parameter_arr = task_parameter_arr[(task_parameter_arr['name'] != task_name[0]) & (task_parameter_arr['map name'] == map_name) | (task_parameter_arr['map name'] != map_name)]
            task_parameter_arr.to_json(file_paths.map.tasks_parameters, indent=2, date_format='iso')
            logger.info('Backend: Task parameters are successfully removed from tasks_parameters.json')
        tasks.saved = task_arr
        tasks.saved_parameters = task_parameter_arr
        current_task.create()
    except Exception as e:
        logger.error('Backend: Could not remove task data from file')
        logger.debug(str(e))

def update_task_preview(task_arr: pd.DataFrame, new_preview: pd.DataFrame) -> None:
    new_preview['map name'] = current_map.name
    new_preview['task nr'] = 0
    new_preview['name'] = current_task.subtasks['name'].unique()[0]
    task_to_update = task_arr[(task_arr['map name'] == current_map.name)&(task_arr['name'] == current_task.subtasks['name'].unique()[0])]
    task_to_update = task_to_update[task_to_update['type'] != 'preview route']
    task_to_update = pd.concat([new_preview, task_to_update], ignore_index=True)
    task_arr = task_arr[(task_arr['map name'] == current_map.name)&(task_arr['name'] != current_task.subtasks['name'].unique()[0]) | (task_arr['map name'] != current_map.name)]
    task_arr = pd.concat([task_arr, task_to_update], ignore_index=True)
    task_arr.to_json(file_paths.map.tasks, indent=2, date_format='iso')
    logger.info('Task preview data are successfully saved in tasks.json')
    tasks.saved = task_arr
    
if __name__ == '__main__':
    read()