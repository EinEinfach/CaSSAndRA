import logging
logger = logging.getLogger(__name__)

#package imports
import os
import json
from dataclasses import dataclass

ABSOLUTE_PATH = os.path.dirname(__file__)

#rovercfg class
@dataclass
class RoverCfg:
    mowspeed_setpoint: float = 0.3
    gotospeed_setpoint: float = 0.5
    positionmode: str = 'relative'
    log: float = 0
    lat: float = 0

    def read_rovercfg(self) -> None:
        try:
            with open(ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
                path_to_data = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not read rovercfg.json. Missing datacfg.json')
            logger.debug(str(e))
            return
        try:
            path_to_rovercfg = path_to_data['path'][0]['user'][3]['rovercfg']
            with open(ABSOLUTE_PATH.replace('/src/backend/data', path_to_rovercfg)) as f: 
                rovercfg_from_file = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not read rovercfg.json. Missing rovercfg.json. Go with standard values')
            logger.debug(str(e))
            res = self.save_rovercfg()
            return
        try:
            logger.debug('Backend: rovercfg to read: '+ str(rovercfg_from_file))
            self.mowspeed_setpoint = rovercfg_from_file['mowspeed_setpoint']
            self.gotospeed_setpoint = rovercfg_from_file['gotospeed_setpoint']
            self.positionmode = rovercfg_from_file['positionmode']
            self.lon = rovercfg_from_file['lon']
            self.lat = rovercfg_from_file['lat']
        except Exception as e:
            logger.error('Backend: Could not read rovercfg.json. Data are invalid. Go with standard values')
            res = self.save_rovercfg()
    
    def save_rovercfg(self) -> int:
        try:
            with open(ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
                path_to_data = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not save rovercfg.json. Missing datacfg.json')
            logger.debug(str(e))
            return -1
        try:
            path_to_rovercfg = path_to_data['path'][0]['user'][3]['rovercfg']
            new_data = dict()
            new_data['mowspeed_setpoint'] = self.mowspeed_setpoint
            new_data['gotospeed_setpoint'] = self.gotospeed_setpoint
            new_data['positionmode'] = self.positionmode
            new_data['lon'] = self.lon
            new_data['lat'] = self.lat
            with open(ABSOLUTE_PATH.replace('/src/backend/data', path_to_rovercfg), 'w') as f:
                logger.debug('New rovercfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('Backend: rovercfg data are successfully stored in rovercfg.json')
            return 0
        except Exception as e:
            logger.error('Backend: Could not save rovercfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1

#coverage path planner config class
@dataclass
class PathPlannerCfg:
    pattern: str() = 'lines'
    width: float = 0.18
    angle: int = 0
    distancetoborder: int = 1
    mowarea: str() = 'yes'
    mowborder: str() = 'yes'
    mowexclusion: str() = 'yes'
    mowborderccw: str() = 'yes'

    def read_pathplannercfg(self) -> None:
        try:
            with open(ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
                path_to_data = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not read pathplannercfg.json. Missing datacfg.json')
            logger.debug(str(e))
            return
        try:
            path_to_pathplannercfg = path_to_data['path'][0]['user'][4]['pathplannercfg']
            with open(ABSOLUTE_PATH.replace('/src/backend/data', path_to_pathplannercfg)) as f: 
                pathplannercfg_from_file = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not read pathplannercfg.json. Missing pathplannercfg.json. Go with standard values')
            logger.debug(str(e))
            res = self.save_pathplannercfg()
            return
        try:
            logger.debug('Backend: pahtplannercfg to read: '+ str(pathplannercfg_from_file))
            self.pattern = pathplannercfg_from_file['pattern']
            self.width = pathplannercfg_from_file['width']
            self.angle = pathplannercfg_from_file['angle']
            self.distancetoborder = pathplannercfg_from_file['distancetoborder']
            self.mowarea = pathplannercfg_from_file['mowarea']
            self.mowborder = pathplannercfg_from_file['mowborder']
            self.mowexclusion = pathplannercfg_from_file['mowexclusion']
            self.mowborderccw = pathplannercfg_from_file['mowborderccw']
        except Exception as e:
            logger.error('Backend: Could not read pathplannercfg.json. Data are invalid. Go with standard values')
            res = self.save_pathplannercfg()
    
    def save_pathplannercfg(self) -> int:
        try:
            with open(ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
                path_to_data = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not save pathplannercfg.json. Missing datacfg.json')
            logger.debug(str(e))
            return -1
        try:
            path_to_pathplannercfg = path_to_data['path'][0]['user'][4]['pathplannercfg']
            new_data = dict()
            new_data['pattern'] = self.pattern
            new_data['width'] = self.width
            new_data['angle'] = self.angle
            new_data['distancetoborder'] = self.distancetoborder
            new_data['mowarea'] = self.mowarea
            new_data['mowborder'] = self.mowborder
            new_data['mowexclusion'] = self.mowexclusion
            new_data['mowborderccw'] = self.mowborderccw
            with open(ABSOLUTE_PATH.replace('/src/backend/data', path_to_pathplannercfg), 'w') as f:
                logger.debug('New pathplannercfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('Backend: pathplannercfg data are successfully stored in pathplannercfg.json')
            return 0
        except Exception as e:
            logger.error('Backend: Could not save pathplannercfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1

rovercfg = RoverCfg()
rovercfg.read_rovercfg()
pathplannercfg = PathPlannerCfg()
pathplannercfg.read_pathplannercfg()
pathplannercfgstate = PathPlannerCfg()
pathplannercfgstate.read_pathplannercfg()


        