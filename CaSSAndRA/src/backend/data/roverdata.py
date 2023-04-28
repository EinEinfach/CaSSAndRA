import logging
logger = logging.getLogger(__name__)
import pandas as pd

#measured
state = pd.DataFrame()
stats = pd.DataFrame()
props = pd.DataFrame()
online = pd.DataFrame()

#calced
calced_from_state = pd.DataFrame()
calced_from_stats = pd.DataFrame()

#commanded
cmd_move = [0, 0]
last_cmd = pd.DataFrame()
current_task = pd.DataFrame()





