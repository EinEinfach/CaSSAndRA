import logging
logger = logging.getLogger(__name__)
import json
import os

from ..data import mapdata, appdata
from src.backend.data.mapdata import current_map, mapping_maps

file_paths = None

def read_commcfg(path_to_cfg_data) -> dict():
    logger.debug('Opening commcfg.json')
    try:
        logger.debug('Path to commcfg.json: '+path_to_cfg_data)
        with open(path_to_cfg_data) as f:
            connect_data = json.load(f)
            logger.debug('commcfg.json content: '+str(connect_data))
            appdata.commcfg = connect_data
    except Exception as e:
        logger.error('Backend: Failed to load communication config file. Missing file')
        logger.debug(str(e))
        return dict()
    f.close()

    logger.info('Backend: Used connection: '+str(connect_data['USE']))
    logger.debug('Checking connection data')
    if connect_data['USE'] == 'MQTT':
        try:
            check = [connect_data['MQTT'][0]['CLIENT_ID'], connect_data['MQTT'][1]['USERNAME'], 
                            connect_data['MQTT'][2]['PASSWORD'], connect_data['MQTT'][3]['MQTT_SERVER'], 
                            connect_data['MQTT'][4]['PORT'], connect_data['MQTT'][5]['MOWER_NAME']]
            logger.debug('Connection data are valid')
            return connect_data
        except Exception as e:
            logger.error('Backend: Failed to load communication config file. Data are invalid')
            logger.debug(str(e))

    elif connect_data['USE'] == 'HTTP':
        try:
            check = [connect_data['HTTP'][0]['IP'], connect_data['HTTP'][1]['PASSWORD']]
            logger.debug('Connection data are valid')
            return connect_data
        except Exception as e:
            logger.error('Backend: Failed to load communication config file. Data are invalid')
            logger.debug(str(e))
            return dict()
    
    elif connect_data['USE'] == 'UART':
        try:
            check = [connect_data['UART'][0]['SERPORT'], connect_data['UART'][1]['BAUDRATE']]
            logger.debug('Connection data are valid')
            return connect_data
        except Exception as e:
            logger.error('Backend: Failed to load communication config file. Data are invalid')
            logger.debug(str(e))
            return dict()
    
    else:
        logger.error('Backend: No valid connection type found. Pls use HTTP, MQTT or UART')
        return dict()

def read_mapcfg(absolute_path):
    logger.debug('Opening mapcfg.json')
    try:
        path_to_cfg_data = file_paths.user.mapcfg
        logger.debug('Path to mapcfg.json: '+path_to_cfg_data)
        with open(path_to_cfg_data) as f:
            mapcfg = json.load(f)
            logger.debug('mapcfg.json content: '+str(mapcfg))
            mapdata.mowoffset = mapcfg['MOWOFFSET']
            mapdata.mowangle = mapcfg['MOWANGLE']
            mapdata.mowedge = mapcfg['MOWEDGE']
            mapdata.distancetoborder = mapcfg['DISTANCETOBORDER']
            mapdata.pattern = mapcfg['PATTERN']
            mapdata.positionmode = mapcfg['POSITIONMODE']
            mapdata.lon = mapcfg['LON']
            mapdata.lat = mapcfg['LAT']
    except Exception as e:
        logger.error('Backend: Failed to load map config file. Missing file or invalid data.')
        logger.info('Backend: Create mapcfg with default values: Mowoffset: 0.18; Mowangle: 0; Mowedge: Yes; Distance to border: 1; Pattern: lines')
        logger.info('Backend: Positionmode: absolute, lon: 0.0, lat: 0.0')
        logger.debug(str(e))
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

    logger.debug('Values for mapcfg. mowoffset: '+str(mapdata.mowoffset)+' mowangle: '+str(mapdata.mowangle)+
                 ' distance to border: '+str(mapdata.distancetoborder) +' pattern: '+mapdata.pattern +' mowedge: '+mapdata.mowedge)

def read_appcfg(absolute_path):
    logger.debug('Opening appcfg.json')
    try:
        path_to_cfg_data = file_paths.user.appcfg
        logger.debug('Path to appcfg.json: '+path_to_cfg_data)
        with open(path_to_cfg_data) as f:
            appcfg = json.load(f)
            logger.debug('appcfg.json content: '+str(appcfg))
            appdata.datamaxage = appcfg['datamaxage']
            appdata.time_to_offline = appcfg['time_to_offline']
            appdata.soc_lookup_table = appcfg['voltage_to_soc']
            appdata.current_thd_charge = appcfg['current_thd_charge']
    except Exception as e:
        logger.error('Backend: Failed to load app config file. Missing file or invalid data.')
        logger.debug(str(e))
        logger.info('Backend: Create appcfg with default values')
        appdata.datamaxage = 30
        appdata.time_to_offline = 60
        appdata.soc_lookup_table = [{'V': 23.5, 'SoC': 0}, {'V': 28.0, 'SoC': 100}]
        appdata.current_thd_charge = -0.03
    
    logger.debug('Values for appcfg. datamaxage: '+str(appdata.datamaxage)+' time until offline: '+str(appdata.time_to_offline)
                 +' soc look up table: '+str(appdata.soc_lookup_table))

def save_commcfg(changed_data: dict()) -> None:
    logger.info('Backend: Writing new connection data to the file')
    try:
        path_to_cfg_data = file_paths.user.comm
        logger.debug('Path to commcfg.json: '+ path_to_cfg_data)
        with open(path_to_cfg_data) as f:
            connect_data = json.load(f)
    except Exception as e:
        logger.error('Backend: Failed to load communication config file.')
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
        with open(path_to_cfg_data, 'w') as f:
            logger.debug('New connect data: '+str(connect_data))
            json.dump(connect_data, f, indent=4)
        logger.info('Backend: Connection data are successfully stored in commcfg.json')
    except Exception as e:
        logger.error('Backend: Could not save connection data to the file')
        logger.debug(str(e))

def save_mapcfg(changed_data: dict()):
    logger.info('Backend: Writing new map and position data to the file')
    try:
        path_to_cfg_data = file_paths.user.mapcfg
        logger.debug('Path to mapcfg.json: '+ path_to_cfg_data)
        with open(path_to_cfg_data) as f:
            map_data = json.load(f)
    except Exception as e:
        logger.error('Backend: Failed to load map config file.')
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
        with open(path_to_cfg_data, 'w') as f:
            logger.debug('New map data: '+str(map_data))
            json.dump(map_data, f, indent=4)
        logger.info('Backend: Map data are successfully stored in mapcfg.json')
    except Exception as e:
        logger.error('Backend: Could not save map data to the file')
        logger.debug(str(e))
    
def save_appcfg(changed_data: dict()):
    logger.info('Backend: Writing new app data to the file')
    try:
        path_to_cfg_data = file_paths.user.appcfg
        logger.debug('Path to appcfg.json: '+str(path_to_cfg_data))
        with open(path_to_cfg_data) as f:
            app_data = json.load(f)
    except Exception as e:
        logger.error('Backend: Failed to load app config file.')
        logger.debug(str(e))
        return
    f.close()
    try: 
        app_data['datamaxage'] = changed_data['datamaxage']
        app_data['time_to_offline'] = changed_data['time_to_offline']
        app_data['current_thd_charge'] = changed_data['current_thd_charge']
        app_data['voltage_to_soc'][0]['V'] = changed_data['voltage_to_soc'][0]['V']
        app_data['voltage_to_soc'][1]['V'] = changed_data['voltage_to_soc'][1]['V']
        with open(path_to_cfg_data, 'w') as f:
            logger.debug('New app data: '+str(app_data))
            json.dump(app_data, f, indent=4)
        logger.info('Backend: App data are successfully stored in appcfg.json')
    except Exception as e:
        logger.error('Backend: Could not save app data to the file')
        logger.debug(str(e))

# if __name__ == '__main__':
#     read_commcfg()
