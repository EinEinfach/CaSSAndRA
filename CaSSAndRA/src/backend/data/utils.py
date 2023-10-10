import os
import shutil
from collections import namedtuple

import logging
logger = logging.getLogger(__name__)

file_paths = namedtuple('FilePaths', ['src', 'user', 'measure', 'map'])
file_paths.user = namedtuple('UserConfigPaths', ['comm', 'mapcfg', 'appcfg', 'rovercfg', 'pathplannercfg', 'schedulecfg'])
file_paths.measure = namedtuple('MeasureConfigPaths', ['state', 'stats', 'props', 'calcedstate', 'calcedstats'])
file_paths.map = namedtuple("MapFilePaths", ['perimeter', 'tasks', 'tasks_parameters'])


def create_missing_files(src_dir, dest_dir):
    # Create the destination directory if it doesn't exist
    if not os.path.exists(dest_dir):
        logger.debug(f'Backend: Creating directory {dest_dir}')
        os.makedirs(dest_dir)
    else:
        logger.debug(f'Backend: Using existing directory {dest_dir}')

    # Iterate over each file and sub-directory in the source directory
    for item in os.listdir(src_dir):
        src_item_path = os.path.join(src_dir, item)
        dest_item_path = os.path.join(dest_dir, item)

        # If it's a file and does not exist in the destination directory, copy it
        if os.path.isfile(src_item_path):
            if not os.path.exists(dest_item_path):
                logger.debug(f'Backend: Copying initial data file from {src_item_path} to {dest_item_path}')
                shutil.copy(src_item_path, dest_item_path)
            else:
                logger.debug(f'Backend: Using existing file {dest_item_path}')
                
        # If it's a directory, recurse into it
        elif os.path.isdir(src_item_path):
            create_missing_files(src_item_path, dest_item_path)



def init_data(data_path):

    # if not os.path.exists(data_path):
    #     os.makedirs(data_path)

    file_paths.src = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    file_paths.data = data_path

    # user config files
    file_paths.user.comm = os.path.join(data_path, 'user', 'commcfg.json')
    file_paths.user.mapcfg = os.path.join(data_path, 'user', 'mapcfg.json')
    file_paths.user.appcfg = os.path.join(data_path, 'user', 'appcfg.json')
    file_paths.user.rovercfg = os.path.join(data_path, 'user', 'rovercfg.json')
    file_paths.user.pathplannercfg = os.path.join(data_path, 'user', 'pathplannercfg.json')
    file_paths.user.schedulecfg = os.path.join(data_path, 'user', 'schedulecfg.json')

    # measure and state files
    file_paths.measure.state = os.path.join(data_path, 'measure', 'state.pickle')
    file_paths.measure.stats = os.path.join(data_path, 'measure', 'stats.pickle')
    file_paths.measure.props = os.path.join(data_path, 'measure', 'props.pickle')
    file_paths.measure.calcedstate = os.path.join(data_path, 'measure', 'calcstate.pickle')
    file_paths.measure.calcedstats = os.path.join(data_path, 'measure', 'calcstats.pickle')

    # map files
    file_paths.map.perimeter = os.path.join(data_path, 'map', 'perimeter.json')
    file_paths.map.tasks = os.path.join(data_path, 'map', 'tasks.json')
    file_paths.map.tasks_parameters = os.path.join(data_path, 'map', 'tasks_parameters.json')
    file_paths.map.tmp = os.path.join(data_path, 'map', 'tmp.json')

    # log files
    file_paths.log = os.path.join(data_path, 'log', 'cassandra.log')

    # initialize data folder from initial data, copying only what is missing
    create_missing_files(os.path.join(file_paths.src, 'data'), data_path)

    return file_paths