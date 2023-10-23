import logging
logger = logging.getLogger(__name__)

import pandas as pd
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Charts():
    live_update: bool = False

chartsdata = Charts()