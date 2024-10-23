import logging
logger = logging.getLogger(__name__)

#packege imports
import pandas as pd
from datetime import datetime
from shapely import Polygon

#local imports
from . import roverdata, calceddata
from ..comm.robotinterface import robotInterface
# from . roverdata import robot
from . mapdata import current_map
from . cfgdata import appcfg

def create_obstacle(data: list) -> pd.DataFrame:
    list_for_df = []
    number_of_points = data[0]
    del data[0]
    for i in range(number_of_points):
        list_for_df.append([data[2*i], data[2*i+1]])
    list_for_df.append([data[0], data[1]])
    # center = list(Polygon(list_for_df).centroid.coords)
    # center_df = pd.DataFrame(center)
    # center_df.columns = ['X', 'Y']
    # center_df['type'] = 'center'
    obstacle_df = pd.DataFrame(list_for_df)
    obstacle_df.columns = ['X', 'Y']
    obstacle_df['type'] = 'points'
    # obstacle_df = pd.concat([obstacle_df, center_df], ignore_index=True)
    obstacleCRCx = obstacle_df['X']*100 
    obstacleCRCy = obstacle_df['Y']*100 
    obstacle_CRC = int(obstacleCRCx.sum() + obstacleCRCy.sum())
    obstacle_df['CRC'] = obstacle_CRC
    return obstacle_df

def add_props_to_df_from_mqtt(data: dict) -> None:
    try: 
        props_to_df = {'firmware':data['firmware'],
                    'version':data['version'],
                    'timestamp': str(datetime.now())
                    }
        props_to_df = pd.DataFrame(data=props_to_df, index=[0])
        roverdata.props = pd.concat([roverdata.props, props_to_df], ignore_index=True)
    except:
        logger.warning('Backend: Received props message is not valid and will be ignored')

def add_online_to_df_from_mqtt(data: str) -> None:
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
    

def add_props_to_df_from_http(data: str) -> None:
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
    
def add_obstacles_to_df(data: str) -> None:
    try: 
        obstacles = current_map.obstacles
        data_list = data.split(',')
        del data_list[-1]
        del data_list[0]
        if len(data_list) == 1:
            if appcfg.obstacles_amount == 0: #Synchronize to sunray fw
                obstacles = pd.DataFrame()
        else:     
            obstacles_number = int(data_list[0]) 
            del data_list[0]
            data_list = [float(x) if '.' in x else int(x) for x in data_list]
            for i in range(obstacles_number):
                obstacle = create_obstacle(data_list[3:4+2*data_list[3]])
                if obstacles.empty or obstacles[obstacles['CRC'] == obstacle['CRC'].unique()[0]].empty:
                    obstacles = pd.concat([obstacles, obstacle], ignore_index=True)
                del data_list[0:4+2*data_list[3]]
            #check of max amount of obstacles
            if appcfg.obstacles_amount != 0:
                if not obstacles.empty and len(obstacles['CRC'].unique()) > appcfg.obstacles_amount:
                    obstacles_crc = obstacles['CRC'].unique()
                    obstacles_crc = obstacles_crc[-appcfg.obstacles_amount:]
                    obstacles = obstacles[obstacles['CRC'].isin(obstacles_crc)]
                    obstacles = obstacles.reset_index(drop=True)
        if not obstacles.equals(current_map.obstacles):
            current_map.add_obstacles(obstacles)
    except Exception as e:
        logger.error('Backend: Failed to write obstacles data to data frame')
        logger.error(str(e))
