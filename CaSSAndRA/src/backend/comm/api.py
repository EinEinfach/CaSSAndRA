import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
import json
import pandas as pd

from .. data.mapdata import current_map, current_task, mapping_maps, tasks
from .. data.scheduledata import schedule_tasks
from .. data.cfgdata import schedulecfg, pathplannercfgapi, commcfg, rovercfg
from .. map import path, map
from .. comm.connections import mqttapi
from .. comm.messageservice import messageservice
from .. data.roverdata import robot
from .robotinterface import robotInterface

from icecream import ic

@dataclass
class API:
    apistate: str = 'boot'
    robotstate: dict = field(default_factory=dict)
    tasksstate: dict = field(default_factory=dict)
    mapsstate: dict = field(default_factory=dict)
    mowparametersstate: dict = field(default_factory=dict)
    mapstate: dict = field(default_factory=dict)
    coordsstate: dict = field(default_factory=dict)
    settingsstate: dict = field(default_factory=dict)
    robotstate_json: str = '{}'
    tasksstate_json: str = '{}'
    mapsstate_json: str = '{}'
    mowparametersstate_json: str = '{}'
    mapstate_json: str ='{}'
    coordsstate_json: str = '{}'
    settingsstate_json: str = '{}'
    loaded_tasks: list = field(default_factory=list)
    commanded_object: str = ''
    command: str = ''
    value: list = field(default_factory=list)
    restart_server: bool = False

    def create_api_payload(self) -> None:
        self.apistate = 'ready'
    
    def create_robot_payload(self) -> None:
        self.robotstate['firmware'] = robot.fw
        self.robotstate['version'] = robot.fw_version
        self.robotstate['status'] = robot.status
        self.robotstate['dockReason'] = robot.dock_reason
        self.robotstate['battery'] = dict(soc=robot.soc, voltage=robot.battery_voltage, electricCurrent=robot.amps)
        self.robotstate['position'] = dict(x=robot.position_x, y=robot.position_y)
        self.robotstate['target'] = dict(x=robot.target_x, y=robot.target_y) 
        self.robotstate['angle'] = robot.position_delta
        self.robotstate['mowPointIdx'] = int(robot.position_mow_point_index)
        self.robotstate['gps'] = dict(visible = int(robot.position_visible_satellites), dgps=int(robot.position_visible_satellites_dgps), age=robot.position_age_hr, solution= robot.solution)
        self.robotstate['secondsPerIdx'] = robot.seconds_per_idx
        self.robotstate['speed'] = robot.speed
        self.robotstate['averageSpeed'] = robot.average_speed
        self.robotstate_json = json.dumps(self.robotstate)

    def create_maps_payload(self) -> None:
        self.mapsstate['loaded'] = current_map.name
        if not mapping_maps.saved.empty:
            self.mapsstate['available'] = list(mapping_maps.saved['name'].unique())
        else:
            self.mapsstate['available'] = []
        self.mapsstate = self.mapsstate
        self.mapsstate_json = json.dumps(self.mapsstate)
    
    def create_tasks_payload(self) -> None:
        if not current_task.subtasks.empty:
            self.tasksstate['selected'] = list(current_task.subtasks['name'].unique())
            self.tasksstate['loaded'] = self.loaded_tasks
        else:
            self.tasksstate['selected'] = []
            self.tasksstate['loaded'] = self.loaded_tasks
        if not tasks.saved.empty:
            self.tasksstate['available'] = list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())
        else:
            self.tasksstate['available'] = []
        self.tasksstate_json = json.dumps(self.tasksstate)
    
    def create_mow_parameters_payload(self) -> None:
        self.mowparametersstate['pattern'] = pathplannercfgapi.pattern
        self.mowparametersstate['width'] = pathplannercfgapi.width
        self.mowparametersstate['angle'] = pathplannercfgapi.angle
        self.mowparametersstate['distancetoborder'] = pathplannercfgapi.distancetoborder
        self.mowparametersstate['mowarea'] = pathplannercfgapi.mowarea
        self.mowparametersstate['mowborder'] = pathplannercfgapi.mowborder
        self.mowparametersstate['mowexclusion'] = pathplannercfgapi.mowexclusion
        self.mowparametersstate['mowborderccw'] = pathplannercfgapi.mowborderccw
        self.mowparametersstate_json = json.dumps(self.mowparametersstate)
    
    def create_map_payload(self) -> None:
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
        self.mapstate_json = json.dumps(self.mapstate)
    
    def create_current_map_coords_payload(self) -> None:
        self.coordsstate = current_map.perimeter_to_geojson()
        self.coordsstate_json = json.dumps(self.coordsstate)
    
    def create_preview_coords_payload(self) -> None:
        self.coordsstate = current_map.preview_to_geojson()
        self.coordsstate_json = json.dumps(self.coordsstate)
    
    def create_mowpath_coords_payload(self) -> None:
        self.coordsstate = current_map.mowpath_to_gejson()
        self.coordsstate_json = json.dumps(self.coordsstate)
    
    def create_obstacles_coords_payload(self) -> None:
        self.coordsstate = current_map.obstacles_to_gejson()
        self.coordsstate_json = json.dumps(self.coordsstate)

    def create_tasks_coords_payload(self, task_name: str) -> None:
        self.coordsstate = tasks.task_to_gejson(task_name)
        self.coordsstate_json = json.dumps(self.coordsstate)
    
    def create_maps_coords_payload(self) -> None:
        self.coordsstate = mapping_maps.maps_to_geojson()
        self.coordsstate_json = json.dumps(self.coordsstate)
    
    def create_settings_payload(self) -> None:
        self.settingsstate['robotConnectionType'] = commcfg.use
        self.settingsstate['httpRobotIpAdress'] = commcfg.http_ip
        self.settingsstate['httpRobotPassword'] = commcfg.http_pass
        self.settingsstate['mqttClientId'] = commcfg.mqtt_client_id
        self.settingsstate['mqttUser'] = commcfg.mqtt_username
        self.settingsstate['mqttPassword'] = commcfg.mqtt_pass
        self.settingsstate['mqttServer'] = commcfg.mqtt_server
        self.settingsstate['mqttPort'] = commcfg.mqtt_port
        self.settingsstate['mqttMowerNameWithPrefix'] = commcfg.mqtt_mower_name 
        self.settingsstate['uartPort'] = commcfg.uart_port
        self.settingsstate['uartBaudrate'] = commcfg.uart_baudrate
        self.settingsstate['apiType'] = commcfg.api
        self.settingsstate['apiMqttClientId'] = commcfg.api_mqtt_client_id
        self.settingsstate['apiMqttUser'] = commcfg.api_mqtt_username
        self.settingsstate['apiMqttPassword'] = commcfg.api_mqtt_pass
        self.settingsstate['apiMqttServer'] = commcfg.api_mqtt_server
        self.settingsstate['apiMqttCassandraServerName'] = commcfg.api_mqtt_cassandra_server_name
        self.settingsstate['apiMqttPort'] = commcfg.api_mqtt_port
        self.settingsstate['messageServiceType'] = commcfg.message_service
        self.settingsstate['telegramApiToken'] = commcfg.telegram_token
        self.settingsstate['telegramChatId'] = commcfg.telegram_chat_id
        self.settingsstate['pushoverApiToken'] = commcfg.pushover_token
        self.settingsstate['pushoverAppName'] = commcfg.pushover_user
        self.settingsstate['robotPositionMode'] = rovercfg.positionmode
        self.settingsstate['longtitude'] = rovercfg.lon
        self.settingsstate['latitude'] = rovercfg.lat
        self.settingsstate['transitSpeedSetPoint'] = rovercfg.gotospeed_setpoint
        self.settingsstate['mowSpeedSetPoint'] = rovercfg.mowspeed_setpoint
        self.settingsstate['fixTimeout'] = rovercfg.fix_timeout
        self.settingsstate_json = json.dumps(self.settingsstate)
        
    def update_payload(self) -> None:
        self.create_api_payload()
        self.create_robot_payload()
        self.create_maps_payload()
        self.create_tasks_payload()
        self.create_mow_parameters_payload()
        self.create_map_payload()
    
    def publish(self, topic: str, message: str) -> None:
        mqttapi.api_publish(topic, message)

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
        # elif 'mow parameters' in buffer:
        #     self.commanded_object = 'mow parameters'
        #     buffer = buffer['mow parameters']
        #     self.check_mow_parameters_cmd(buffer)
        elif 'map' in buffer:
            self.commanded_object = 'map'
            buffer = buffer['map']
            self.check_map_cmd(buffer)
        elif 'coords' in buffer:
            self.commanded_object = 'coords'
            buffer = buffer['coords']
            self.check_coords_cmd(buffer)
        elif 'settings' in buffer:
            self.commanded_object = 'settings'
            buffer = buffer['settings']
            self.check_settings_cmd(buffer)
        elif 'server' in buffer:
            self.commanded_object = 'server'
            buffer = buffer['server']
            self.check_server_cmd(buffer)
        else:
            logger.info('No valid object in api message found. Aborting')

    def check_tasks_cmd(self, buffer: dict) -> None:
        allowed_cmds = ['select', 'load']
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
        allowed_cmds = ['select', 'load']
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
        allowed_cmds = ['mow', 'stop', 'dock', 'move', 'reboot', 'shutdown', 'set mow speed', 'set goto speed', 'set mow progress', 'go to']
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
    
    def perform_mow_parameters_cmd(self, buffer: dict) -> None:
        buffer = buffer['value']
        if 'mowPattern' in buffer:
            allowed_values = ['lines', 'squares', 'rings']
            pattern = buffer['mowPattern']
            value = list(set([pattern]).intersection(allowed_values))
            if value != []:
                pathplannercfgapi.pattern = value[0]
                logger.info(f'Mow parameter pattern changed to: {value[0]}')
            else:
                logger.info(f'No valid value for pattern found. Allowed values: {allowed_values}')
        if 'width' in buffer:
            try:
                value = float(buffer['width'])
                if 0.01 < value <= 1:
                    pathplannercfgapi.width = value
                    logger.info(f'Mow parameter width changed to: {value}')
                else:
                    logger.info(f'Wrong range of width value')
            except Exception as e:
                logger.info(f'Width value is invalid')
                logger.debug(str(e))
        if 'angle' in buffer:
            try:
                value = int(buffer['angle'])
                if 0 <= value <= 359:
                    pathplannercfgapi.angle = value
                    logger.info(f'Mow parameter angle changed to: {value}')
                else:
                    logger.info(f'Wrong range of angle value')
            except Exception as e:
                logger.info(f'Angle value is invalid')
                logger.debug(str(e))
        if 'distanceToBorder' in buffer:
            try:
                value = int(buffer['distanceToBorder'])
                if 0 <= value <= 5:
                    pathplannercfgapi.distancetoborder = value
                    logger.info(f'Mow parameter distance to border changed to: {value}')
                else:
                    logger.info(f'Wrong range of distance to border value')
            except Exception as e:
                logger.info(f'Distance to border value is invalid')
                logger.debug(str(e))
        if 'mowArea' in buffer:
            try:
                value = bool(buffer['mowArea'])
                pathplannercfgapi.mowarea = value
                logger.info(f'Mow parameter mow area changed to: {value}')
            except Exception as e:
                logger.info(f'Mow area value is invalid')
                logger.debug(str(e))
        if 'borderLaps' in buffer:
            try:
                value = int(buffer['borderLaps'])
                if 0 <= value <= 5:
                    pathplannercfgapi.mowborder = value
                    logger.info(f'Mow parameter mow border changed to: {value}')
                else:
                    logger.info(f'Wrong range of mow border value')
            except Exception as e:
                logger.info(f'Mow border value is invalid')
                logger.debug(str(e))
        if 'mowExclusionBorder' in buffer:
            try:
                value = bool(buffer['mowExclusionBorder'])
                pathplannercfgapi.mowexclusion = value
                logger.info(f'Mow parameter mow exclusion changed to: {value}')
            except Exception as e:
                logger.info(f'Mow exclusion value is invalid')
                logger.debug(str(e))
        if 'mowBorderCcw' in buffer:
            try:
                value = bool(buffer['mowBorderCcw'])
                pathplannercfgapi.mowborderccw = value
                logger.info(f'Mow parameter mow border in ccw changed to: {value}')
            except Exception as e:
                logger.info(f'Mow border in ccw value is invalid')
                logger.debug(str(e))
    
    def check_map_cmd(self, buffer) -> None:
        allowed_values = ['setSelection', 'setMowParameters', 'resetObstacles']
        command = list(set([buffer['command']]).intersection(allowed_values))
        if command != []:
            if command[0] == 'setSelection':
                self.perform_map_set_selection_cmd(buffer)
            elif command[0] == 'setMowParameters':
                self.perform_mow_parameters_cmd(buffer)
            elif command[0] == 'resetObstacles':
                self.perform_reset_obstacles_cmd()
        else:
            logger.info(f'No valid command in api message found. Allowed commands: {allowed_values}. Aborting')
    
    def check_coords_cmd(self, buffer) -> None:
        allowed_values = ['update']
        if 'command' in buffer:
            command = [buffer['command']]
            command = list(set(command).intersection(allowed_values))
            if command == []:
                logger.info(f'No valid value in api message found. Allowed commands: {allowed_values}. Aborting')
            else:
                if command[0] == 'update':
                    self.perform_coords_cmd(buffer)
        else:
            logger.info(f'No valid api message for coords command. Aborting')
    
    def check_settings_cmd(self, buffer) -> None:
        allowed_values = ['update', 'setComm', 'setRover']
        if 'command' in buffer:
            command = [buffer['command']]
            command = list(set(command).intersection(allowed_values))
            if command == []:
                logger.info(f'No valid value in api message found. Allowed commands: {allowed_values}. Aborting')
            else:
                if command[0] == 'update':
                    self.perform_settings_update_cmd()
                elif command [0] == 'setComm':
                    self.perform_set_comm_settings_cmd(buffer)
                elif command[0] == 'setRover':
                    self.perform_set_rover_settings_cmd(buffer)
        else:
            logger.info(f'No valid api message for settings command. Aborting')
    
    def check_server_cmd(self, buffer) -> None:
        allowed_values = ['restart', 'sendMessage']
        if 'command' in buffer:
            command = [buffer['command']]
            command = list(set(command).intersection(allowed_values))
            if command == []:
                logger.info(f'No valid value in api message found. Allowed commands: {allowed_values}. Aborting')
            else:
                if command[0] == 'restart':
                    self.restart_server = True
                elif command[0] == 'sendMessage' and 'value' in buffer:
                    messageservice.send_message(buffer['value'][0])
        else:
            logger.info(f'No valid api message for server command. Aborting')

    def perform_tasks_cmd(self, buffer: dict) -> None:
        if 'value' in buffer:
            value = buffer['value']
            if value == []:
                current_task.subtasks = pd.DataFrame()
                current_task.subtasks_parameters = pd.DataFrame()
                return
            allowed_values = list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())
            try:
                tasks_to_load = []
                for task in value: #Workaround to keep order of tasks after intersection call
                    tasks_to_load.append(list(set([task]).intersection(list(tasks.saved[tasks.saved['map name'] == current_map.name]['name'].unique())))[0])
                self.value = tasks_to_load
                if self.value == []:
                    logger.info(f'No valid value in api message found. Allowed values: {allowed_values}. Aborting')
                else:
                    if self.command == 'select':
                        current_task.load_task_order(self.value)
                        for value in self.value:
                            self.perform_task_coords_cmd(value)
                    elif self.command == 'load':
                        self.loaded_tasks = self.value
                        current_task.load_task_order(self.value)
                        current_map.task_progress = 0
                        current_map.calculating = True
                        path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
                        current_map.calculating = False
                        current_map.calc_route_mowpath()
                        #cmdlist.cmd_take_map = True
                        robotInterface.performCmd('sendMap')
            except Exception as e:
                logger.info(f'No valid value in api message found. Allowed values: {allowed_values}. Aborting')
                logger.debug(f'{e}')

    def perform_maps_cmd(self, buffer: dict) -> None:
        if 'value' in buffer:
            value = buffer['value']
            try:
                self.value = list(set(value).intersection(list(mapping_maps.saved['name'].unique())))
                if self.command == 'load' and self.value != []:
                    selected = mapping_maps.saved[mapping_maps.saved['name'] == self.value[0]] 
                    current_map.perimeter = selected
                    current_map.create(self.value[0])
                    current_task.create()
                    schedule_tasks.create()
                    schedulecfg.reset_schedulecfg()
                    #cmdlist.cmd_take_map = True
                    robotInterface.performCmd('sendMap')
                if self.command == 'select' and self.value != []:
                    mapping_maps.select_saved(mapping_maps.saved[mapping_maps.saved['name'] == self.value[0]])
                    self.create_maps_coords_payload()
                    self.publish('mapsCoords', self.coordsstate_json)
                if self.command == 'select' and self.value == []:
                    mapping_maps.init()
                    self.publish('mapsCoords', json.dumps(dict()))
            except Exception as e:
                logger.error(f'Geojson maps export failed. Aborting')
                logger.error(f'{e}')

    def perform_robot_cmd(self, buffer) -> None:
        try:
            if self.command == 'stop':
                # cmdlist.cmd_stop = True
                robotInterface.performCmd('stop')
            elif self.command == 'dock':
                # cmdlist.cmd_dock = True
                robotInterface.performCmd('dock')
            elif self.command == 'mow':
                self.value = buffer['value'][0]
                self.perform_mow_cmd()
            elif self.command == 'go to':
                self.value = buffer['value']
                self.perform_goto_cmd()
            elif self.command == 'move':
                robot.cmd_move_lin = buffer['value'][0]
                robot.cmd_move_ang = buffer['value'][1]
                # cmdlist.cmd_move = True
                robotInterface.performCmd('move')
            elif self.command == 'reboot':
                # cmdlist.cmd_reboot = True
                robotInterface.performCmd('reboot')
            elif self.command == 'shutdown':
                # cmdlist.cmd_shutdown = True
                robotInterface.performCmd('shutdown')
            elif self.command == 'set mow speed':
                robot.mowspeed_setpoint = buffer['value'][0]
                # cmdlist.cmd_changemowspeed = True
                robotInterface.performCmd('changeMowSpeed')
            elif self.command == 'set goto speed':
                robot.gotospeed_setpoint = buffer['value'][0]
                # cmdlist.cmd_changegotospeed = True
                robotInterface.performCmd('changeGoToSpeed')
            elif self.command == 'set mow progress':
                robot.mowprogress = buffer['value'][0]
                # cmdlist.cmd_skiptomowprogress = True
                robotInterface.performCmd('skipToMowProgress')
            else:
                logger.warning(f'No valid command in api message found. Aborting')
        except Exception as e:
            logger.error(f'Perform api robot command triggered exception. Aborting')
            logger.debug(f'{e}')

    def perform_mow_cmd(self) -> None:
        allowed_values = ['resume', 'task', 'all', 'selection']
        if self.value == 'resume':
            #cmdlist.cmd_resume = True
            robotInterface.performCmd('resume')
        elif self.value == 'task':
            if self.tasksstate['selected'] != []:
                current_map.task_progress = 0
                current_map.calculating = True
                path.calc_task(current_task.subtasks, current_task.subtasks_parameters)
                current_map.calculating = False
                current_map.calc_route_mowpath()
                robotInterface.performCmd('mow')
                # cmdlist.cmd_mow = True
            else:
                logger.info(f'No selected tasks found')
        elif self.value == 'all':
            current_map.selected_perimeter = current_map.perimeter_polygon
            current_map.calculating = True
            current_map.task_progress = 0
            current_map.total_tasks = 1
            route = path.calc_simple(current_map.selected_perimeter, pathplannercfgapi)
            if route:
                current_map.areatomow = round(current_map.selected_perimeter.area)
                current_map.calc_route_preview(route) 
            current_map.calculating = False
            current_map.calc_route_mowpath()
            robotInterface.performCmd('mow')
            # cmdlist.cmd_mow = True
        elif self.value == 'selection':
            if 'selection' in self.mapstate:
                current_map.selected_perimeter = map.selection(current_map.perimeter_polygon, self.mapstate['selection'])
                current_map.calculating = True
                current_map.task_progress = 0
                current_map.total_tasks = 1
                route = path.calc_simple(current_map.selected_perimeter, pathplannercfgapi)
                if route:
                    current_map.calc_route_preview(route)
                    current_map.areatomow = round(current_map.selected_perimeter.area)
                current_map.calculating = False
                current_map.calc_route_mowpath()
                robotInterface.performCmd('mow')
                # cmdlist.cmd_mow = True
            else:
                logger.info(f'No selection found')
        else:
            logger.info(f'No valid value in api message found. Allowed values: {allowed_values}. Aborting')
    
    def perform_goto_cmd(self) -> None:
        if 'x' in self.value and 'y' in self.value:
            try:
                current_map.gotopoint = pd.DataFrame(self.value)
                current_map.gotopoint.columns = ['X', 'Y']
                current_map.gotopoint['type'] = 'way'
                #cmdlist.cmd_goto = True
                robotInterface.performCmd('goTo')
            except Exception as e:
                logger.info('Go to point invalid')
                logger.debug(str(e))
    
    def perform_map_set_selection_cmd(self, buffer) -> None:
        if 'value' in buffer and 'x' in buffer['value'] and 'y' in buffer['value']:
            try:
                self.mapstate['selection'] = dict(api=buffer['value'])
            except Exception as e:
                logger.info('Selection invalid')
                logger.debug(str(e)) 
    
    def perform_reset_obstacles_cmd(self) -> None:
        current_map.add_obstacles(pd.DataFrame())
    
    def perform_coords_cmd(self, buffer) -> None:
        allowed_values = ['currentMap', 'preview', 'mowPath', 'obstacles']
        if 'value' in buffer:
            for value in buffer['value']:
                if value == 'currentMap':
                    self.create_current_map_coords_payload()
                    self.publish('coords', self.coordsstate_json)
                if value == 'preview':
                    self.create_preview_coords_payload()
                    self.publish('coords', self.coordsstate_json)
                if value == 'mowPath':
                    self.create_mowpath_coords_payload()
                    self.publish('coords', self.coordsstate_json)
                if value == 'obstacles':
                    self.create_obstacles_coords_payload()
                    self.publish('coords', self.coordsstate_json)
    
    def perform_task_coords_cmd(self, task_name: str) -> None:
        self.create_tasks_coords_payload(task_name)
        self.publish('coords', self.coordsstate_json)
    
    def perform_settings_update_cmd(self) -> None:
        self.create_settings_payload()
        self.publish('settings', self.settingsstate_json)
    
    def perform_set_comm_settings_cmd(serlf, buffer) -> None:
        try:
            buffer = buffer['value'] 
            for key in buffer:
                if key == 'robotConnectionType':
                    commcfg.use = buffer[key]
                if key == 'httpRobotIpAdress':
                    commcfg.http_ip = buffer[key]
                if key == 'httpRobotPassword':
                    commcfg.http_pass = buffer[key]
                if key == 'mqttClientId':
                    commcfg.mqtt_client_id = buffer[key]
                if key == 'mqttUser':
                    commcfg.mqtt_username = buffer[key]
                if key == 'mqttPassword':
                    commcfg.mqtt_pass = buffer[key]
                if key == 'mqttServer':
                    commcfg.mqtt_server = buffer[key]
                if key == 'mqttPort':
                    commcfg.mqtt_port = buffer[key]
                if key == 'mqttMowerNameWithPrefix':
                    commcfg.mqtt_mower_name = buffer[key]
                if key == 'uartPort':
                    commcfg.uart_port = buffer[key]
                if key == 'uartBaudrate':
                    commcfg.uart_baudrate = buffer[key]
                if key == 'apiType':
                    commcfg.api = buffer[key]
                if key == 'apiMqttClientId':
                    commcfg.api_mqtt_client_id = buffer[key]
                if key == 'apiMqttUser':
                    commcfg.api_mqtt_username = buffer[key]
                if key == 'apiMqttPassword':
                    commcfg.api_mqtt_pass = buffer[key]
                if key == 'apiMqttServer':
                    commcfg.api_mqtt_server = buffer[key]
                if key == 'apiMqttCassandraServerName':
                    commcfg.api_mqtt_cassandra_server_name = buffer[key]
                if key == 'apiMqttPort':
                    commcfg.api_mqtt_port = buffer[key]
                if key == 'messageServiceType':
                    if buffer[key] == 'telegram':
                        commcfg.message_service = 'Telegram'
                    elif buffer[key] == 'pushover':
                        commcfg.message_service = 'Pushover'
                    else:
                        commcfg.message_service = None
                if key == 'telegramApiToken':
                    commcfg.telegram_token = buffer[key]
                if key == 'telegramChatId':
                    commcfg.telegram_chat_id = buffer[key]
                if key == 'pushoverApiToken':
                    commcfg.pushover_token = buffer[key]
                if key == 'pushoverAppName':
                    commcfg.pushover_user = buffer[key]
            commcfg.save_commcfg()

        except Exception as e:
            logger.error('Perform set comm settings command triggered an error. Aborrting')
            logger.debug(f'{e}')

    def perform_set_rover_settings_cmd(serlf, buffer) -> None:
        try:
            buffer = buffer['value'] 
            for key in buffer:
                if key == 'robotPositionMode':
                    rovercfg.positionmode = buffer[key]
                if key == 'longtitude':
                    rovercfg.lon = buffer[key]
                if key == 'latitude':
                    rovercfg.lat = buffer[key]
            rovercfg.save_rovercfg()
            robotInterface.performCmd('setPositionMode')

        except Exception as e:
            logger.error('Perform set rover settings command triggered an error. Aborrting')
            logger.debug(f'{e}')



cassandra_api = API()