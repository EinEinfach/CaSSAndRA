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
            logger.error('Backend: Could not read rovercfg.json. Missing rovercfg.json')
            logger.debug(str(e))
            return
        try:
            self.mowspeed_setpoint = rovercfg_from_file['mowspeed_setpoint']
            self.gotospeed_setpoint = rovercfg_from_file['gotospeed_setpoint']
        except Exception as e:
            logger.error('Backend: Could not read rovercfg.json. Data are invalid. Go with standar values')
    
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
            with open(ABSOLUTE_PATH.replace('/src/backend/data', path_to_rovercfg), 'w') as f:
                logger.debug('New rovercfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('Backend: rovercfg data are successfully stored in rovercfg.json')
            return 0
        except Exception as e:
            logger.error('Backend: Could not save rovercfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1
            
rovercfg = RoverCfg()
rovercfg.read_rovercfg()


        