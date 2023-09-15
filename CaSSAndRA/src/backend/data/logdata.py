import logging
logger = logging.getLogger(__name__)

import pandas as pd
from datetime import datetime
from dataclasses import dataclass
import os

ABSOLUTE_PATH = os.path.dirname(__file__)

df = pd.read_csv('CaSSAndRA/src/data/log/cassandra.log', sep=';')
df.columns = ['time', 'content']
df = df[df['time'].str.contains('2023')]
df = df.tail(100)
df = df.iloc[::-1]

@dataclass
class Log():
    lastdata: pd.DataFrame = pd.DataFrame()
    path = ABSOLUTE_PATH.replace('/src/backend/data', '/src/data/log/cassandra.log')

    def read(self) -> None:
        try:
            logger.debug('Reading cassandra.log')
            data = pd.read_csv(self.path, sep=';')
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