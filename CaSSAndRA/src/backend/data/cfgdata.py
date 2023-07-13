import logging
logger = logging.getLogger(__name__)

#package imports
import os
import json
from dataclasses import dataclass
import base64
import pandas as pd

ABSOLUTE_PATH = os.path.dirname(__file__)

#appcfg class
@dataclass
class AppCfg:
    datamaxage: int = 30
    time_to_offline: int = 60
    voltage_0: float = 22
    voltage_100: float = 28
    current_thd_charge: float = -0.03
    rover_picture: str = 'default/'

    def read_appcfg(self) -> None:
        try:
            with open(ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
                path_to_data = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not read appcfg.json. Missing datacfg.json')
            logger.debug(str(e))
            return
        try:
            path_to_appcfg = path_to_data['path'][0]['user'][2]['appcfg']
            with open(ABSOLUTE_PATH.replace('/src/backend/data', path_to_appcfg)) as f: 
                appcfg_from_file = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not read appcfg.json. Missing appcfg.json. Go with standard values')
            logger.debug(str(e))
            res = self.save_appcfg()
            return
        try:
            logger.debug('Backend: appcfg to read: '+ str(appcfg_from_file))
            self.datamaxage = appcfg_from_file['datamaxage']
            self.time_to_offline = appcfg_from_file['time_to_offline']
            self.voltage_0 = appcfg_from_file['voltage_to_soc'][0]['V']
            self.voltage_100 = appcfg_from_file['voltage_to_soc'][1]['V']
            self.current_thd_charge = appcfg_from_file['current_thd_charge']
            self.rover_picture = appcfg_from_file['rover_picture']
        except Exception as e:
            logger.error('Backend: Could not read rovercfg.json. Data are invalid. Go with standard values')
            res = self.save_appcfg()
    
    def save_appcfg(self) -> int:
        try:
            with open(ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/datacfg.json')) as f: 
                path_to_data = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Backend: Could not save appcfg.json. Missing datacfg.json')
            logger.debug(str(e))
            return -1
        try:
            path_to_appcfg = path_to_data['path'][0]['user'][2]['appcfg']
            new_data = dict()
            new_data['datamaxage'] = self.datamaxage
            new_data['time_to_offline'] = self.time_to_offline
            soc_look_up_table = [{'V': self.voltage_0, 'SoC': 0}, {'V': self.voltage_100, 'SoC': 100}]
            new_data['voltage_to_soc'] = soc_look_up_table
            new_data['current_thd_charge'] = self.current_thd_charge
            new_data['rover_picture'] = self.rover_picture
            with open(ABSOLUTE_PATH.replace('/src/backend/data', path_to_appcfg), 'w') as f:
                logger.debug('New appcfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('Backend: rovercfg data are successfully stored in appcfg.json')
            return 0
        except Exception as e:
            logger.error('Backend: Could not save appcfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1
    
    def show_preview_image(self, path: str) -> str:
        encoded_image = base64.b64encode(open(os.path.dirname(__file__).replace('/backend/data', '/assets/icons/'+path+'rover90grad.png'), 'rb').read())
        return 'data:image/png;base64,{}'.format(encoded_image.decode()) 

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
    mowborder: int = 1
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
    
    def df_to_obj(self, parameters: pd.DataFrame) -> None:
        self.pattern = parameters.iloc[0]['pattern']
        self.width = parameters.iloc[0]['width']
        self.angle = parameters.iloc[0]['angle']
        self.distancetoborder = parameters.iloc[0]['distancetoborder']
        self.mowarea = parameters.iloc[0]['mowarea']
        self.mowborder = parameters.iloc[0]['mowborder']
        self.mowexclusion = parameters.iloc[0]['mowexclusion']
        self.mowborderccw = parameters.iloc[0]['mowborderccw']

rovercfg = RoverCfg()
rovercfg.read_rovercfg()
pathplannercfg = PathPlannerCfg()
pathplannercfg.read_pathplannercfg()
pathplannercfgstate = PathPlannerCfg()
pathplannercfgstate.read_pathplannercfg()
pathplannercfgtask = PathPlannerCfg()
pathplannercfgtask.read_pathplannercfg()
pathplannercfgtasktmp = PathPlannerCfg()
pathplannercfgtasktmp.read_pathplannercfg()
appcfg = AppCfg()
appcfg.read_appcfg()


        