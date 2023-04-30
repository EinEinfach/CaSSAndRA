import logging
logger = logging.getLogger(__name__)
import pandas as pd

from .. data import mapdata
from .. map import map, preview

def perimeter(perimeter_arr: pd.DataFrame(), nr) -> bool:
    logger.info('Backend: Changing perimeter to nr: '+str(nr))
    try:
        mapdata.perimeter = mapdata.imported[mapdata.imported['map_nr'] == nr]
        mapdata.perimeter = mapdata.perimeter.reset_index(drop=True)
        #Create goto points if Map Data availible
        if not mapdata.perimeter.empty:
            perimeter = map.create(mapdata.perimeter)
            gotopoints = map.gotopoints(perimeter, 0.5)
            preview.gotopoints(gotopoints)    
        return 0
    except Exception as e:
        logger.warning('Backend: Could not change perimeter')
        logger.debug(str(e))
        return -1