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

def add_online_to_df_from_http(data: bool) -> None:
    if data:
        online_to_df = {'online': True,
                        'timestamp': str(datetime.now())}
    else:
        online_to_df = {'online': False,
                        'timestamp': str(datetime.now())}
    online_to_df = pd.DataFrame(data=online_to_df, index=[0])
    roverdata.online = pd.concat([roverdata.online, online_to_df], ignore_index=True)