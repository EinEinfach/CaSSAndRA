import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
import json

from .. data.mapdata import current_map, current_task, mapping_maps, tasks
from .. data.scheduledata import schedule_tasks
from .. data.cfgdata import schedulecfg
from .. map import path
from .. comm import cmdlist
from .. data.roverdata import robot

from icecream import ic

@dataclass
class API:
    apistate: str = 'boot'
    robotstate: str = 'offline'
    taskstate: str = '{}'
    mapsstate: str = '{}'
    commanded_object: str = ''
    command: str = ''
    value: str = ''

    def create_api_payload(self) -> None:
        self.apistate = 'ready'

    def create_robot_payload(self) -> None:
        self.robotstate = robot.status

    def create_maps_payload(self) -> None:
        mapsstate = dict()
        mapsstate['loaded'] = current_map.name
        if not mapping_maps.saved.empty:
            mapsstate['available'] = list(mapping_maps.saved['name'].unique())
        else:
            mapsstate['available'] = []
        self.mapsstate = json.dumps(mapsstate)
    
    def create_tasks_payload(self) -> None:
        taskstate = dict()
        if not current_task.subtasks.empty:
            taskstate['selected'] = list(current_task.subtasks['name'].unique())
        else:
            taskstate['selected'] = []
        if not tasks.saved.empty:
            taskstate['available'] = list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())
        else:
            taskstate['available'] = []
        self.taskstate = json.dumps(taskstate)
    
    def update_payload(self) -> None:
        self.create_api_payload()
        self.create_robot_payload()
        self.create_maps_payload()
        self.create_tasks_payload()

    def check_cmd(self, buffer: dict) -> None:
        if 'tasks' in buffer:
            self.commanded_object = 'tasks'
            buffer = buffer['tasks']
            self.check_tasks_cmd(buffer)
        elif 'maps' in buffer:
            self.commanded_object = 'maps'
            buffer = buffer['maps']
            self.check_maps_cmd(buffer)
        elif 'robot' in buffer:
            self.commanded_object = 'robot'
            buffer = buffer['robot']
            self.check_robot_cmd(buffer)
        else:
            logger.info('No valid object in api message found. Aborting')
            return

    def check_tasks_cmd(self, buffer: dict) -> None:
        allowed_cmds = ['load', 'start']
        if 'command' in buffer:
            command = [buffer['command']]
            command = list(set(command).intersection(allowed_cmds))
            if command == []:
                logger.info(f'No valid command in api message found. Allowed commands: {allowed_cmds}. Aborting')
            else:
                self.command = command[0]
                self.perform_tasks_cmd(buffer)
        else:
           logger.info('No command in api message found. Aborting')
        return 
    
    def check_maps_cmd(self, buffer: dict) -> None:
        allowed_cmds = ['load']
        if 'command' in buffer:
            command = [buffer['command']]
            command = list(set(command).intersection(allowed_cmds))
            if command == []:
                logger.info(f'No valid command in api message found. Allowed commands: {allowed_cmds}. Aborting')
            else:
                self.command = command[0]
                self.perform_maps_cmd(buffer)
        else:
           logger.info('No command in api message found. Aborting')
        return 

    def check_robot_cmd(self, buffer: dict) ->  None:
        allowed_cmds = ['start', 'stop', 'dock', 'resume']
        if 'command' in buffer:
            command = [buffer['command']]
            command = list(set(command).intersection(allowed_cmds))
            if command == []:
                logger.info(f'No valid command in api message found. Allowed commands: {allowed_cmds}. Aborting')
            else:
                self.command = command[0]
                self.perform_robot_cmd(buffer)
        else:
           logger.info('No command in api message found. Aborting')
        return 
    
    def perform_tasks_cmd(self, buffer: dict) -> None:
        if 'value' in buffer:
            value = buffer['value']
            self.value = list(set(value).intersection(list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())))
            if self.value == []:
                allowed_values = list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())
                logger.info(f'No valid value in api message found. Allowed values: {allowed_values}. Aborting')
            else:
                if self.command == 'load':
                    current_task.load_task_order(self.value)
                    current_map.task_progress = 0
                    current_map.calculating = True
                    path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
                    current_map.calculating = False
                    current_map.mowpath = current_map.preview
                    current_map.mowpath['type'] = 'way'
                    cmdlist.cmd_take_map = True
                elif self.command == 'start':
                    current_task.load_task_order(self.value)
                    current_map.task_progress = 0
                    current_map.calculating = True
                    path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
                    current_map.calculating = False
                    current_map.mowpath = current_map.preview
                    current_map.mowpath['type'] = 'way'
                    cmdlist.cmd_mow = True

    def perform_maps_cmd(self, buffer: dict) -> None:
        if 'value' in buffer:
            value = buffer['value']
            self.value = list(set(value).intersection(list(mapping_maps.saved['name'].unique())))
            if self.value == []:
                allowed_values = list(mapping_maps.saved['name'].unique())
                logger.info(f'No valid value in api message found. Allowed values: {allowed_values}. Aborting')
            else:
                if self.command == 'load':
                    selected = mapping_maps.saved[mapping_maps.saved['name'] == self.value[0]] 
                    current_map.perimeter = selected
                    current_map.create(self.value[0])
                    current_task.create()
                    schedule_tasks.create()
                    schedulecfg.reset_schedulecfg()
                    cmdlist.cmd_take_map = True

    def perform_robot_cmd(self, buffer: dict) -> None:
        pass
    
cassandra_api = API()