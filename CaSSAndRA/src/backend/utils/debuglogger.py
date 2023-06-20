import logging
logger = logging.getLogger(__name__)

def log(value_to_log):
    if value_to_log == None:
        value_to_log = 'empty string'
    logger.error('###########Debug logger##########: '+value_to_log)