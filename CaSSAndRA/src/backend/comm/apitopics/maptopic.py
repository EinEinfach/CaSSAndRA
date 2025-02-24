import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field

import json
import pandas as pd

from ...data.mapdata import current_map
from ...data.cfgdata import pathplannercfgapi
from .robottopic import robotTopic

@dataclass
class MapTopic:
    mapstate: dict = field(default_factory=dict)
    mapstateJson: str = '{}'
    coordsstate: dict = field(default_factory=dict)
    coordsstateJson: list = field(default_factory=list)
    allowedCmds: list = field(default_factory=lambda: ['setSelection', 'setMowParameters', 'resetObstacles', 'resetRoute'])
    allowedMowCmdVal: list = field(default_factory=lambda: [])
    allowedCoordsCmds: list = field(default_factory=lambda: ['update'])
    allowedCoordsVal: list = field(default_factory=lambda: ['currentMap', 'preview', 'mowPath', 'obstacles'])

    def createPayload(self) -> dict:
        try:
            self.mapstate['mapId'] = current_map.map_id
            self.mapstate['previewId'] = current_map.previewId
            self.mapstate['mowPathId'] = current_map.mowpathId
            self.mapstate['obstaclesId'] = current_map.obstaclesId
            self.mapstate['mowprogressIdxPercent'] = current_map.idx_perc
            self.mapstate['mowprogressDistancePercent'] = current_map.distance_perc
            self.mapstate['finishedDistance'] = current_map.finished_distance
            self.mapstate['distanceTotal'] = current_map.distance
            self.mapstate['finishedIdx'] = int(current_map.finished_idx)
            self.mapstate['idxTotal'] = int(current_map.idx)
            self.mapstate['areaTotal'] = int(current_map.areatomow) 
            self.mapstateJson = json.dumps(self.mapstate)
            return self.mapstateJson
        except Exception as e:
            logger.error('Could not create api map payload.')
            logger.error(str(e))
            return dict()
    
    def checkCmd(self, buffer: dict) ->  None:
        try:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedCmds))
            if command == []:
                logger.info(f'No valid command in api message for map topic found. Allowed commands: {self.allowedCmds}. Aborting')
            else:
                self._performCmd(command[0], buffer)
        except Exception as e:
            logger.error('Api command for map topic is invalid')
            logger.error(str(e))
    
    def checkCoordsCmd(self, buffer: dict) ->  None:
        try:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedCoordsCmds))
            if command == []:
                logger.info(f'No valid command in api message for coords coords map coords topic found. Allowed commands: {self.allowedCoordsCmds}. Aborting')
            else:
                self._performCoordsCmd(command[0], buffer)
        except Exception as e:
            logger.error('Api command for map coords topic is invalid')
            logger.error(str(e))
    
    def _performCmd(self, command: str, buffer: dict) -> None:
        try:
            if command == 'setSelection':
                self._setSelection(buffer)
            elif command == 'setMowParameters':
                self._setMowParameters(buffer)
            elif command == 'resetObstacles':
                self._resetObstacles(buffer)
            elif command == 'resetRoute':
                self._resetRoute(buffer)
        except Exception as e:
            logger.error(f'Api value for maps command is invalid')
            logger.debug(f'{e}')
    
    def _performCoordsCmd(self, command: str, buffer: dict) -> None:
        try:
            if command == 'update':
                self._updateCoords(buffer)
        except Exception as e:  
            logger.error(f'Api value for map coords command is invalid')
            logger.debug(f'{e}')
    
    def _setSelection(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            robotTopic.mapData['selection'] = dict(api=value)
        except Exception as e:
            logger.error('Api value for set selection on map command invalid')
            logger.error(str(e))
    
    def _setMowParameters(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            allowedPattern = ['lines', 'squares', 'rings']
            pattern = value['mowPattern']
            pattern = list(set([pattern]).intersection(allowedPattern))
            if pattern != []:
                pathplannercfgapi.pattern = pattern[0]
                logger.debug(f'Mow parameter pattern changed to: {pattern[0]}')

            width = float(value['width'])
            if 0.01 < width <= 1:
                pathplannercfgapi.width = width
                logger.debug(f'Mow parameter width changed to: {width}')

            angle = int(value['angle'])
            if 0 <= angle <= 359:
                pathplannercfgapi.angle = angle
                logger.debug(f'Mow parameter angle changed to: {angle}')
          
            distanceToBorder = int(value['distanceToBorder'])
            if 0 <= distanceToBorder <= 5:
                pathplannercfgapi.distancetoborder = distanceToBorder
                logger.debug(f'Mow parameter distance to border changed to: {distanceToBorder}')
            
            mowArea = bool(value['mowArea'])
            pathplannercfgapi.mowarea = mowArea
            logger.debug(f'Mow parameter mow area changed to: {mowArea}')
                
            borderLaps = int(value['borderLaps'])
            if 0 <= borderLaps <= 5:
                pathplannercfgapi.mowborder = borderLaps
                logger.debug(f'Mow parameter mow border changed to: {borderLaps}')
                   
            mowExclusionBorder = bool(value['mowExclusionBorder'])
            pathplannercfgapi.mowexclusion = mowExclusionBorder
            logger.debug(f'Mow parameter mow exclusion changed to: {mowExclusionBorder}')
               
            mowBorderCcw = bool(value['mowBorderCcw'])
            pathplannercfgapi.mowborderccw = mowBorderCcw
            logger.debug(f'Mow parameter mow border in ccw changed to: {mowBorderCcw}')
    
        except Exception as e:
            logger.error('Api value for set mow parameters on map command invalid')
            logger.error(str(e))
    
    def _resetObstacles(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            current_map.add_obstacles(pd.DataFrame())
        except Exception as e:
            logger.error('Api value for reset obstacles on map command invalid')
            logger.error(str(e))

    def _resetRoute(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            current_map.clear_route_mowpath()
        except Exception as e:
            logger.error('Api value for reset route on map command invalid')
            logger.error(str(e))
    
    def _updateCoords(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            value = list(set(value).intersection(self.allowedCoordsVal))
            if value == []:
                logger.info(f'No valid value in api message for map coords update command found. Allowed values: {self.allowedCoordsVal}. Aborting')
                return
            for item in value:
                if item == 'currentMap':
                    self.coordsstate = current_map.perimeter_to_geojson()
                    self.coordsstateJson.append(json.dumps(self.coordsstate))
                elif item == 'preview':
                    self.coordsstate = current_map.preview_to_geojson()
                    self.coordsstateJson.append(json.dumps(self.coordsstate))
                elif item == 'mowPath':
                    self.coordsstate = current_map.mowpath_to_gejson()
                    self.coordsstateJson.append(json.dumps(self.coordsstate)) 
                elif item == 'obstacles':
                    self.coordsstate = current_map.obstacles_to_gejson()
                    self.coordsstateJson.append(json.dumps(self.coordsstate))
        except Exception as e:
            logger.error('Api value for update coords on map command invalid')
            logger.error(str(e))

mapTopic = MapTopic()
    


