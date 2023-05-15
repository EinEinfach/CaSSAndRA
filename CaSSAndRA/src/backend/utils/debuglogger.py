import logging
logger = logging.getLogger(__name__)

def log(value_to_log):
    logger.error('###########Debug logger##########: '+value_to_log)