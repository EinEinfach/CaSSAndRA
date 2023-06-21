import logging
logger = logging.getLogger(__name__)

#packege imports
import pandas as pd
from datetime import datetime, timedelta

#local imports
from . import roverdata, appdata
from . cfgdata import appcfg

def check(data_clean_finished: bool) -> bool:
    now = datetime.now()
    if now.hour == 0 and not data_clean_finished:
        logger.info('Backend: Cleaning meausered and calced data. Max age: '+str(appcfg.datamaxage)+' days')
        delta_time = str(datetime.now() - timedelta(appcfg.datamaxage))

        #Clean state data 
        state = roverdata.state[(roverdata.state['timestamp'] > delta_time)]
        logger.debug('state data: '+str(len(roverdata.state[(roverdata.state['timestamp'] <= delta_time)]))+' rows will be droped')
        state = state.reset_index(drop=True)
        roverdata.state = state

        #Clean stats data 
        stats = roverdata.stats[(roverdata.stats['timestamp'] > delta_time)]
        logger.debug('stats data: '+str(len(roverdata.stats[(roverdata.stats['timestamp'] <= delta_time)]))+' rows will be droped')
        stats = stats.reset_index(drop=True)
        roverdata.stats = stats

        #Clean props data 
        try:
            props = roverdata.props[(roverdata.props['timestamp'] > delta_time)]
            logger.debug('props data: '+str(len(roverdata.props[(roverdata.props['timestamp'] <= delta_time)]))+' rows will be droped')
            props = props.reset_index(drop=True)
            roverdata.props = props
        except:
            logger.debug('props data: nothing to clean')

        #Clean online data 
        try: 
            online = roverdata.online[(roverdata.online['timestamp'] > delta_time)]
            logger.debug('online data: '+str(len(roverdata.online[(roverdata.online['timestamp'] <= delta_time)]))+' rows will be droped')
            online = online.reset_index(drop=True)
            roverdata.online = online
        except:
            logger.debug('online data: nothing to clean')

        #Clean calced_from_state data 
        calced_from_state = roverdata.calced_from_state[(roverdata.calced_from_state['timestamp'] > delta_time)]
        logger.debug('calced_from_state data: '+str(len(roverdata.calced_from_state[(roverdata.calced_from_state['timestamp'] <= delta_time)]))+' rows will be droped')
        calced_from_state = calced_from_state.reset_index(drop=True)
        roverdata.calced_from_state = calced_from_state

        #Clean calced_from_stats data 
        calced_from_stats = roverdata.calced_from_stats[(roverdata.calced_from_stats['timestamp'] > delta_time)]
        logger.debug('calced_from_stats data: '+str(len(roverdata.calced_from_stats[(roverdata.calced_from_stats['timestamp'] <= delta_time)]))+' rows will be droped')
        calced_from_stats = calced_from_stats.reset_index(drop=True)
        roverdata.calced_from_stats = calced_from_stats

        data_clean_finished = True

    elif now.hour != 0:
        data_clean_finished = False

    return data_clean_finished


  






