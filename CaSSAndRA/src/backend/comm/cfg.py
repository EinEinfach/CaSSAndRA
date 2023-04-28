import logging
logger = logging.getLogger(__name__)
import json
import os

from ..data import mapdata, appdata

def read_commcfg(absolute_path) -> dict():
    try:
        with open(absolute_path.replace('/src/backend', '/src/data/datacfg.json')) as f:
            path_to_data = json.load(f)
            f.close()
        path_to_cfg_data = path_to_data['path'][0]['user'][0]['comm']
        with open(absolute_path.replace('src/backend', path_to_cfg_data)) as f:
            connect_data = json.load(f)
            appdata.commcfg = connect_data
    except:
        logger.warning('Backend: Failed to load communication config file. Missing file')
        return dict()
    f.close()

    logger.info('Backend: Used connection: '+str(connect_data['USE']))
    if connect_data['USE'] == 'MQTT':
        try:
            check = [connect_data['MQTT'][0]['CLIENT_ID'], connect_data['MQTT'][1]['USERNAME'], 
                            connect_data['MQTT'][2]['PASSWORD'], connect_data['MQTT'][3]['MQTT_SERVER'], 
                            connect_data['MQTT'][4]['PORT'], connect_data['MQTT'][5]['MOWER_NAME']]
            return connect_data
        except:
            logger.warning('Backend: Failed to load communication config file. Data are invalid')

    elif connect_data['USE'] == 'HTTP':
        try:
            check = [connect_data['HTTP'][0]['IP'], connect_data['HTTP'][1]['PASSWORD']]
            return connect_data
        except:
            logger.warning('Backend: Failed to load communication config file. Data are invalid')
            return dict()
    
    elif connect_data['USE'] == 'UART':
        try:
            check = [connect_data['UART'][0]['SERPORT'], connect_data['UART'][1]['BAUDRATE']]
            return connect_data
        except:
            logger.warning('Backend: Failed to load communication config file. Data are invalid')
            return dict()
    
    else:
        logger.warning('Backend: Failed to load communication config file. Data are invalid')
        return dict()

def read_mapcfg(absolute_path):
    try:
        with open(absolute_path.replace('/src/backend', '/src/data/datacfg.json')) as f: 
            path_to_data = json.load(f)
            f.close()
        path_to_cfg_data = path_to_data['path'][0]['user'][1]['mapcfg']
        with open(absolute_path.replace('/src/backend', path_to_cfg_data)) as f:
            mapcfg = json.load(f)
            mapdata.mowoffset = mapcfg['MOWOFFSET']
            mapdata.mowangle = mapcfg['MOWANGLE']
            mapdata.mowedge = mapcfg['MOWEDGE']
            mapdata.distancetoborder = mapcfg['DISTANCETOBORDER']
            mapdata.pattern = mapcfg['PATTERN']
            mapdata.positionmode = mapcfg['POSITIONMODE']
            mapdata.lon = mapcfg['LON']
            mapdata.lat = mapcfg['LAT']
    except:
        logger.warning('Backend: Failed to load map config file. Missing file or invalid data.')
        logger.warning('Backend: Create mapcfg with default values: Mowoffset: 0.18; Mowangle: 0; Mowedge: Yes; Distance to border: 1; Pattern: lines')
        logger.warning('Backend: Positionmode: absolute, lon: 0.0, lat: 0.0')
        mapdata.mowoffset = 0.18
        mapdata.mowangle = 0
        mapdata.mowedge = 'yes'
        mapdata.distancetoborder = 1
        mapdata.pattern = 'lines'
        mapdata.positionmode = 'relative'
        mapdata.lon = 0
        mapdata.lat = 0

    mapdata.mowoffsetstatepage = mapdata.mowoffset
    mapdata.mowanglestatepage = mapdata.mowangle
    mapdata.mowedgestatepage = mapdata.mowedge
    mapdata.distancetoborderstatepage = mapdata.distancetoborder
    mapdata.patternstatepage = mapdata.pattern

    logger.debug('Values for mapcfg. mowoffset:'+str(mapdata.mowoffset)+' mowangle: '+str(mapdata.mowangle)+' distance to border: '+str(mapdata.distancetoborder))

def read_appcfg(absolute_path):
    try:
        with open(absolute_path.replace('/src/backend', '/src/data/datacfg.json')) as f: 
            path_to_data = json.load(f)
            f.close()
        path_to_cfg_data = path_to_data['path'][0]['user'][2]['appcfg']
        with open(absolute_path.replace('/src/backend', path_to_cfg_data)) as f:
            appcfg = json.load(f)
            appdata.datamaxage = appcfg['datamaxage']
            appdata.time_to_offline = appcfg['time_to_offline']
            appdata.soc_lookup_table = appcfg['voltage_to_soc']
            appdata.current_thd_charge = appcfg['current_thd_charge']
    except Exception as e:
        logger.warning('Backend: Failed to load app config file. Missing file or invalid data.')
        logger.debug(str(e))
        logger.warning('Backend: Create appcfg with default values')
        appdata.datamaxage = 30
        appdata.time_to_offline = 60
        appdata.soc_lookup_table = [{'V': 23.5, 'SoC': 0}, {'V': 28.0, 'SoC': 100}]
        appdata.current_thd_charge = -0.03
    
    logger.debug('Values for appcfg. datamaxage: '+str(appdata.datamaxage)+' time until offline: '+str(appdata.time_to_offline))

def save_commcfg(changed_data: dict()) -> None:
    logger.info('Backend: Writing new connection data to the file')
    absolute_path = os.path.dirname(__file__) 
    try:
        with open(absolute_path.replace('/src/backend/comm', '/src/data/datacfg.json')) as f:
            path_to_data = json.load(f)
            f.close()
        path_to_cfg_data = path_to_data['path'][0]['user'][0]['comm']
        with open(absolute_path.replace('src/backend/comm', path_to_cfg_data)) as f:
            connect_data = json.load(f)
    except Exception as e:
        logger.warning('Backend: Failed to load communication config file.')
        logger.debug(str(e))
        return
    f.close()
    try: 
        if changed_data['USE'] == 'MQTT':
            connect_data['USE'] = 'MQTT'
            connect_data['MQTT'][0]['CLIENT_ID'] = changed_data['CLIENT_ID']
            connect_data['MQTT'][1]['USERNAME'] = changed_data['USERNAME']
            connect_data['MQTT'][2]['PASSWORD'] = changed_data['PASSWORD']
            connect_data['MQTT'][3]['MQTT_SERVER'] = changed_data['MQTT_SERVER']
            connect_data['MQTT'][4]['PORT'] = changed_data['PORT']
            connect_data['MQTT'][5]['MOWER_NAME'] = changed_data['MOWER_NAME']
        elif changed_data['USE'] == 'HTTP':
            connect_data['USE'] = 'HTTP'
            connect_data['HTTP'][0]['IP'] = changed_data['IP']
            connect_data['HTTP'][1]['PASSWORD'] = changed_data['PASSWORD']
        elif changed_data['USE'] == 'UART':
            connect_data['USE'] = 'UART'
            connect_data['UART'][0]['SERPORT'] = changed_data['SERPORT']
            connect_data['UART'][1]['BAUDRATE']= changed_data['BAUDRATE']
        with open(absolute_path.replace('/src/backend/comm', path_to_cfg_data), 'w') as f:
            json.dump(connect_data, f, indent=4)
        logger.info('Backend: Connection data are successfully stored in commcfg.json')
    except Exception as e:
        logger.warning('Backend: Could not save connection data to the file')
        logger.debug(str(e))

def save_mapcfg(changed_data: dict()):
    logger.info('Backend: Writing new map and position data to the file')
    absolute_path = os.path.dirname(__file__)
    try:
        with open(absolute_path.replace('/src/backend/comm', '/src/data/datacfg.json')) as f:
            path_to_data = json.load(f)
            f.close()
        path_to_cfg_data = path_to_data['path'][0]['user'][1]['mapcfg']
        with open(absolute_path.replace('src/backend/comm', path_to_cfg_data)) as f:
            map_data = json.load(f)
    except Exception as e:
        logger.warning('Backend: Failed to load map config file.')
        logger.debug(str(e))
        return
    f.close()
    try: 
        map_data['MOWOFFSET'] = changed_data['MOWOFFSET']
        map_data['MOWANGLE'] = changed_data['MOWANGLE']
        map_data['MOWEDGE'] = changed_data['MOWEDGE']
        map_data['DISTANCETOBORDER'] = changed_data['DISTANCETOBORDER']
        map_data['PATTERN'] = changed_data['PATTERN']
        map_data['POSITIONMODE'] = changed_data['POSITIONMODE']
        map_data['LON'] = changed_data['LON']
        map_data['LAT'] = changed_data['LAT']
        with open(absolute_path.replace('/src/backend/comm', path_to_cfg_data), 'w') as f:
            json.dump(map_data, f, indent=4)
        logger.info('Backend: Map data are successfully stored in mapcfg.json')
    except Exception as e:
        logger.warning('Backend: Could not save map data to the file')
        logger.debug(str(e))
    
def save_appcfg(changed_data: dict()):
    logger.info('Backend: Writing new app data to the file')
    absolute_path = os.path.dirname(__file__)
    try:
        with open(absolute_path.replace('/src/backend/comm', '/src/data/datacfg.json')) as f:
            path_to_data = json.load(f)
            f.close()
        path_to_cfg_data = path_to_data['path'][0]['user'][2]['appcfg']
        with open(absolute_path.replace('src/backend/comm', path_to_cfg_data)) as f:
            app_data = json.load(f)
    except Exception as e:
        logger.warning('Backend: Failed to load app config file.')
        logger.debug(str(e))
        return
    f.close()
    try: 
        app_data['datamaxage'] = changed_data['datamaxage']
        app_data['time_to_offline'] = changed_data['time_to_offline']
        app_data['current_thd_charge'] = changed_data['current_thd_charge']
        app_data['voltage_to_soc'][0]['V'] = changed_data['voltage_to_soc'][0]['V']
        app_data['voltage_to_soc'][1]['V'] = changed_data['voltage_to_soc'][1]['V']
        with open(absolute_path.replace('/src/backend/comm', path_to_cfg_data), 'w') as f:
            json.dump(app_data, f, indent=4)
        logger.info('Backend: App data are successfully stored in appcfg.json')
    except Exception as e:
        logger.warning('Backend: Could not save app data to the file')
        logger.debug(str(e))

# if __name__ == '__main__':
#     read_commcfg()
