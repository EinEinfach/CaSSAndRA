import logging
logger = logging.getLogger(__name__)

import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
import os

ABSOLUTE_PATH = os.path.dirname(__file__)

@dataclass
class Log():
    lastdata: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    path = ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/log/cassandra.log')

    def read(self) -> None:
        try:
            logger.debug('Reading cassandra.log')
            data = pd.read_csv(self.path, sep='([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9])', engine='python')
            data = data.drop(data.columns[0], axis=1)
            data = data.dropna()
            today = str(datetime.now().date())
            data = data[data[data.columns[0]].str.contains(today)]
            data = data.tail(1000)
            data = data.iloc[::-1]
            data.columns = ['time', 'message']
            self.lastdata = data
        except Exception as e:
            logger.error('Backend: Could not read cassandra.log file')
            logger.error(str(e))

#create a log instance
commlog = Log()
