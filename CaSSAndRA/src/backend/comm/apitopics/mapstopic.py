import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field

import json

from ...data.mapdata import current_map, current_task, mapping_maps, tasks
from ...data.scheduledata import schedule_tasks
from ...data.cfgdata import schedulecfg
from ...data import saveddata
from ..robotinterface import robotInterface

@dataclass
class MapsTopic:
    mapsstate: dict = field(default_factory=lambda: dict())
    mapsstateJson: str = '{}'
    coordsstate: dict = field(default_factory=lambda: dict())
    coordsstateJson: str = None
    allowedCmds: list = field(default_factory=lambda: ['select', 'load', 'save', 'remove', 'rename', 'copy'])

    def createPayload(self) -> dict:
        try:
            self.mapsstate['loaded'] = current_map.name
            if not mapping_maps.saved.empty:
                self.mapsstate['available'] = list(mapping_maps.saved['name'].unique())
            else:
                self.mapsstate['available'] = []
            self.mapsstateJson = json.dumps(self.mapsstate)
            return self.mapsstateJson
        except Exception as e:
            logger.error('Could not create api maps payload.')
            logger.error(str(e))
            return dict()
    
    def checkCmd(self, buffer: dict) ->  None:
        try:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedCmds))
            if command == []:
                logger.info(f'No valid command in api message for maps topic found. Allowed commands: {self.allowedCmds}. Aborting')
            else:
                self._performCmd(command[0], buffer)
        except Exception as e:
            logger.error('Api command for maps topic is invalid')
            logger.error(str(e))
    
    def _performCmd(self, command: str, buffer: dict) -> None:
        try:
            if command == 'load':
                self._load(buffer)
            elif command == 'select':
                self._select(buffer)
            elif command == 'remove':
                self._remove(buffer)
            elif command == 'save':
                self._save(buffer)
            elif command == 'rename':
                self._rename(buffer)
            elif command == 'copy':
                self._copy(buffer)
        except Exception as e:
            logger.error(f'Api value for maps command is invalid')
            logger.debug(f'{e}')
    
    def _load(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            selected = mapping_maps.saved[mapping_maps.saved['name'] == value[0]] 
            current_map.perimeter = selected
            current_map.create(value[0])
            current_task.create()
            schedule_tasks.create()
            schedulecfg.reset_schedulecfg()
            robotInterface.performCmd('sendMap')
        except Exception as e:
            logger.error('Api value for load maps command invalid')
            logger.error(str(e))
    
    def _select(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            if value != []:
                mapping_maps.select_saved(mapping_maps.saved[mapping_maps.saved['name'] == value[0]])
                self.coordsstate = mapping_maps.maps_to_geojson()
                self.coordsstateJson = json.dumps(self.coordsstate)
            else:
                mapping_maps.init()
                self.coordsstateJson = json.dumps(dict())
        except Exception as e:
            logger.error('Api value for select maps command invalid')
            logger.error(str(e))
            return dict()
    
    def _remove(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            saveddata.remove_perimeter(mapping_maps.saved, value[0], tasks.saved, tasks.saved_parameters)
            if value[0] == current_map.name:
                current_map.clear_map()
                schedule_tasks.create()
                schedulecfg.reset_schedulecfg()
        except Exception as e:
            logger.error('Api value for remove maps command invalid')
            logger.error(str(e))  
    
    def _save(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            res = mapping_maps.import_api_map(value)
            if res[0] == 0:
                saveddata.save_perimeter(mapping_maps.saved, res[1], res[2])
                if res[3] != '':
                    saveddata.copy_tasks(res[3], res[2])
        except Exception as e:
            logger.error('Api value for save maps command invalid')
            logger.error(str(e))  
    
    def _rename(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            saveddata.rename_perimeter(value[0], value[1])
        except Exception as e:
            logger.error('Api value for rename maps command invalid')
            logger.error(str(e))     

    def _copy(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            saveddata.copy_perimeter(mapping_maps.saved, value[0], f'{value[0]}_copy') 
        except Exception as e:
            logger.error('Api value for copy maps command invalid')
            logger.error(str(e))     

mapsTopic = MapsTopic()



