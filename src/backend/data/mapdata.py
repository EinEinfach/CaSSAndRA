import logging
logger = logging.getLogger(__name__)

import pandas as pd
from shapely.geometry import *

perimeter = pd.DataFrame()
preview = pd.DataFrame()
imported = pd.DataFrame()
gotopoints = pd.DataFrame()
gotopoint = pd.DataFrame()
mowpath = pd.DataFrame()
areatomow = float()
distancetogo = float()
#perimeter_for_plot contains the same data as perimeter and aditionaly the first coordiante for perimeter and every exclusion for creating a closed polygon in plot
perimeter_for_plot = pd.DataFrame()

#map interaction data
selected_zone = pd.DataFrame()
zone = pd.DataFrame()

#mow settings from mapcfg.json
mowoffset = float()
mowangle = int()
mowedge = bool()
distancetoborder = int()
pattern = str()

#positionmode from mapcfg.json
positionmode = str()
lon = float()
lat = float()

#mow settings from state page
mowoffsetstatepage = float()
mowanglestatepage = int()
mowedgestatepage = bool()
distancetoborderstatepage = int()
patternstatepage = str()

#temp mapdata
selected_perimeter = Polygon()
