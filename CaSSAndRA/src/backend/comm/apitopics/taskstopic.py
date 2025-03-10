import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
import json
import pandas as pd

from ...data.mapdata import current_map, current_task, tasks
from ...data import cfgdata
from ...data.cfgdata import schedulecfg
from ... map import path, map
from ...data import saveddata
from ..robotinterface import robotInterface

@dataclass
class TasksTopic:
    tasksstate: dict = field(default_factory=dict)
    tasksstateJson: str = '{}'
    coordsstate: dict = field(default_factory=dict)
    coordsstateJson: list = field(default_factory=list)
    schedulecfgstateJson: str = '{}'
    loadedTasks: list = field(default_factory=list)
    allowedCmds: list = field(default_factory=lambda:['select', 'load', 'save', 'calculate', 'remove', 'rename', 'copy'])
    allowedScheduleCmds: list = field(default_factory=lambda:['save'])


    def createPayload(self) -> dict:
        try:
            if not current_task.subtasks.empty:
                self.tasksstate['selected'] = list(current_task.subtasks['name'].unique())
                self.tasksstate['loaded'] = self.loadedTasks
            else:
                self.tasksstate['selected'] = []
                self.tasksstate['loaded'] = self.loadedTasks
            if not tasks.saved.empty:
                self.tasksstate['available'] = list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())
            else:
                self.tasksstate['available'] = []
            self.tasksstateJson = json.dumps(self.tasksstate)
            return self.tasksstateJson
        except Exception as e:
            logger.error('Could not create api tasks payload.')
            logger.error(str(e))
            return dict()
    
    def createSchedulePayload(self) -> dict:
        try:
            self.schedulecfgstateJson = json.dumps(schedulecfg.to_json())
            return self.schedulecfgstateJson
        except Exception as e:
            logger.error('Could not create api schedule payload.')
            logger.error(str(e))
            return dict()

    def checkCmd(self, buffer: dict) -> None:
        try:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedCmds))
            if command == []:
                logger.info(f'No valid command in api message for tasks topic found. Allowed commands: {self.allowedCmds}. Aborting')
            else:
                self._performCmd(command[0], buffer)
        except Exception as e:
            logger.error('Api command for tasks topic is invalid')
            logger.error(str(e))
    
    def checkScheduleCmd(self, buffer: dict) -> None:
        try:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedScheduleCmds))
            if command == []:
                logger.info(f'No valid command in api message for schedule topic found. Allowed commands: {self.allowedScheduleCmds}. Aborting')
            else:
                self._performScheduleCmd(command[0], buffer)
        except Exception as e:
            logger.error('Api command for schedule topic is invalid')
            logger.error(str(e))
    
    def _performCmd(self, command: str, buffer: dict) -> None:
        try:
            if command == 'select':
                self._select(buffer)
            elif command == 'load':
                self._load(buffer)
            elif command == 'save':
                self._save(buffer)
            elif command == 'calculate':
                self._calculate(buffer)
            elif command == 'remove':
                self._remove(buffer)
            elif command == 'rename':
                self._rename(buffer)
            elif command == 'copy': 
                self._copy(buffer)
        except Exception as e:
            logger.error('Api command for tasks topic is invalid')
            logger.error(str(e))
    
    def _performScheduleCmd(self, command: str, buffer: dict) -> None:
        try:
            if command == 'save':
                self._saveSchedule(buffer)
        except Exception as e:  
            logger.error('Api command for schedule topic is invalid')
            logger.error(str(e))
    
    def _select(self, buffer: dict) -> None:
        try:
            tasksToSelect = []
            value = buffer['value']
            for task in value: #Workaround to keep order of tasks after intersection call
                tasksToSelect.append(list(set([task]).intersection(list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())))[0])
            if tasksToSelect == []:
                current_task.subtasks = pd.DataFrame()
                current_task.subtasks_parameters = pd.DataFrame()
                return
            current_task.load_task_order(tasksToSelect)
            for task in tasksToSelect:
                coordsstate = tasks.task_to_gejson(task)
                self.coordsstateJson.append(json.dumps(coordsstate))
        except Exception as e:
            logger.error('Api value for tasks select command is invalid')
            logger.error(str(e))
    
    def _load(self, buffer: dict) -> None:
        try:
            tasksToLoad = []
            value = buffer['value']
            for task in value: #Workaround to keep order of tasks after intersection call
                tasksToLoad.append(list(set([task]).intersection(list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())))[0])
            if tasksToLoad == []:
                return
            current_task.load_task_order(tasksToLoad)
            current_map.task_progress = 0
            current_map.calculating = True
            path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
            current_map.calculating = False
            current_map.calc_route_mowpath()
            robotInterface.performCmd('sendMap')
        except Exception as e:
            logger.error('Api value for tasks load command is invalid')
            logger.error(str(e))
    
    def _save(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            receivedTask, receivedTaskParameters, taskName = current_task.create_subtask_api(value)
            saveddata.save_task(tasks.saved, tasks.saved_parameters, receivedTask, receivedTaskParameters, taskName)
        except Exception as e:
            logger.error('Api value for tasks save command is invalid')
            logger.error(str(e))
    
    def _calculate(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            mowParameters = cfgdata.PathPlannerCfg()
            mowParameters.read_pathplannercfg_from_api(value['features'][1]['properties']['mowParameters'])
            xValues = [coord[0] for coord in value['features'][1]['geometry']['coordinates'][0]]
            yValues = [coord[1] for coord in value['features'][1]['geometry']['coordinates'][0]]
            selection = dict(lassoPoints=dict(x=xValues, y=yValues))
            perimeter = map.selection(current_map.perimeter_polygon, selection)
            preview = path.calc_simple(perimeter, mowParameters)
            preview = pd.DataFrame(preview, columns=['X', 'Y'],)
            previewGeoJson = tasks.preview_to_geojson(preview, 0)
            self.coordsstate = value
            self.coordsstate['features'][0]['properties']['name'] = 'taskPreview'
            self.coordsstate['features'][1]['geometry'] = previewGeoJson['geometry']
            self.coordsstateJson.append(json.dumps(self.coordsstate))
        except Exception as e:
            logger.error('Api value for tasks calculate command is invalid')
            logger.error(str(e))
    
    def _remove(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            saveddata.remove_task(tasks.saved, tasks.saved_parameters, value, current_map.name)
        except Exception as e:
            logger.error('Api value for tasks remove command is invalid')
            logger.error(str(e))
    
    def _rename(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            saveddata.rename_task(value[1], value[0])
        except Exception as e:
            logger.error('Api value for tasks rename command is invalid')
            logger.error(str(e))
    
    def _copy(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            saveddata.copy_task(value[0])
        except Exception as e:
            logger.error('Api value for tasks copy command is invalid')
            logger.error(str(e))
    
    def _saveSchedule(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            if schedulecfg.save_schedulecfg_api(value) == 0:
                newScheduledata = self.createSchedulePayload()
        except Exception as e:
            logger.error('Api value for schedule save command is invalid')
            logger.error(str(e))


tasksTopic = TasksTopic()