import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field

from .. data.cfgdata import commcfg
from .. comm.connections import mqttapi
from .. comm.messageservice import messageservice
from .robotinterface import robotInterface

from .apitopics.robottopic import robotTopic
from .apitopics.mapstopic import mapsTopic
from .apitopics.maptopic import mapTopic
from .apitopics.taskstopic import tasksTopic
from .apitopics.mowparameterstopic import mowParametersTopic
from .apitopics.settingstopic import settingsTopic

from icecream import ic

@dataclass
class API:
    apistate: str = 'boot'
    robotstate_json: str = '{}'
    tasksstate_json: str = '{}'
    mapsstate_json: str = '{}'
    mowparametersstate_json: str = '{}'
    mapstate_json: str ='{}'
    coordsstate_json: str = '{}'
    settingsstate_json: str = '{}'
    schedulecfgstate_json: str = '{}'
    commanded_object: str = ''
    restart_server: bool = False
    shutdown_server: bool = False
    check_auto_shutdown: bool = False
    allowedCmds: list = field(default_factory=lambda: ['shutdown', 'restart', 'sendMessage'])

    def publish(self, topic: str, message: str) -> None:
        mqttapi.api_publish(topic, message)
        
    def updatePayload(self) -> None:
        self.robotstate_json = robotTopic.createPayload()
        self.mapsstate_json = mapsTopic.createPayload()
        self.tasksstate_json = tasksTopic.createPayload()
        self.mowparametersstate_json = mowParametersTopic.createPayload()
        self.mapstate_json = mapTopic.createPayload()
        self.schedulecfgstate_json = tasksTopic.createSchedulePayload()

    def checkCmd(self, buffer: dict) -> None:
        self.apistate = 'busy'
        self.publish('status', self.apistate)
        if 'tasks' in buffer:
            self.commanded_object = 'tasks'
            buffer = buffer['tasks']
            tasksTopic.checkCmd(buffer)
            if tasksTopic.coordsstateJson != []:
                for taskCoords in tasksTopic.coordsstateJson:
                    self.publish('coords', taskCoords)
                tasksTopic.coordsstateJson = []
        elif 'maps' in buffer:
            self.commanded_object = 'maps'
            buffer = buffer['maps']
            mapsTopic.checkCmd(buffer)
            if mapsTopic.coordsstateJson != None:
                self.publish('mapsCoords', mapsTopic.coordsstateJson)
                mapsTopic.coordsstateJson = None
        elif 'robot' in buffer:
            self.commanded_object = 'robot'
            buffer = buffer['robot']
            robotTopic.checkCmd(buffer)
        elif 'map' in buffer:
            self.commanded_object = 'map'
            buffer = buffer['map']
            mapTopic.checkCmd(buffer)
        elif 'coords' in buffer:
            self.commanded_object = 'coords'
            buffer = buffer['coords']
            mapTopic.checkCoordsCmd(buffer)
            if mapTopic.coordsstateJson != []:
                for mapCoords in mapTopic.coordsstateJson:
                    self.publish('coords', mapCoords)
                mapTopic.coordsstateJson = []
        elif 'settings' in buffer:
            self.commanded_object = 'settings'
            buffer = buffer['settings']
            settingsTopic.checkCmd(buffer)
            if settingsTopic.settingsstateJson != None:
                self.publish('settings', settingsTopic.settingsstateJson)
                settingsTopic.settingsstateJson = None
        elif 'server' in buffer:
            self.commanded_object = 'server'
            buffer = buffer['server']
            self._checkServerCmd(buffer)
        elif 'schedule' in buffer:
            self.commanded_object = 'schedule'
            buffer = buffer['schedule']
            tasksTopic.checkScheduleCmd(buffer)
        else:
            logger.info('No valid object in api message found. Aborting')
        self.apistate = 'ready'
        self.publish('status', self.apistate)

    def _checkServerCmd(self, buffer) -> None:
        if 'command' in buffer:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedCmds))
            if command == []:
                logger.info(f'No valid value in api message found. Allowed commands: {self.allowedCmds}. Aborting')
            else:
                if command[0] == 'shutdown':
                    if commcfg.use == 'UART':
                        robotInterface.performCmd('shutdown')
                        self.check_auto_shutdown = True
                    else:
                        self.shutdown_server = True
                elif command[0] == 'restart':
                    self.restart_server = True
                elif command[0] == 'sendMessage' and 'value' in buffer:
                    messageservice.send_message(buffer['value'][0])
        else:
            logger.info(f'No valid api message for server command. Aborting')

cassandra_api = API()