import logging
logger = logging.getLogger(__name__)
import pandas as pd

from .. data import mapdata

def perimeter(perimeter_arr: pd.DataFrame(), nr) -> bool:
    logger.info('Backend: Changing perimeter to nr: '+str(nr))
    try:
        mapdata.perimeter = mapdata.imported[mapdata.imported['map_nr'] == nr]
        mapdata.perimeter = mapdata.perimeter.reset_index(drop=True)
        return 0
    except Exception as e:
        logger.warning('Backend: Could not change perimeter')
        logger.debug(str(e))
        return -1