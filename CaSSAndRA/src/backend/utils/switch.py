import logging
logger = logging.getLogger(__name__)
import pandas as pd

from .. data import mapdata

def perimeter(perimeter_arr: pd.DataFrame(), nr) -> list():
    logger.info('Backend: Changing perimeter to nr: '+str(nr))
    try:
        perimeter = perimeter_arr[perimeter_arr['map_nr'] == nr]
        perimeter = perimeter.reset_index(drop=True)
        #Create goto points if Map Data availible
        # if not mapdata.perimeter.empty:
        #     perimeter = map.create(mapdata.perimeter)
        #     gotopoints = map.gotopoints(perimeter, 0.5)
        #     preview.gotopoints(gotopoints)    
        return 0, perimeter
    except Exception as e:
        logger.warning('Backend: Could not change perimeter')
        logger.debug(str(e))
        return -1, pd.DataFrame()