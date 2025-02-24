import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
import json

from ...data.cfgdata import commcfg, rovercfg
from ..robotinterface import robotInterface

@dataclass
class SettingsTopic:
    settingsstate: dict = field(default_factory=lambda: dict())
    settingsstateJson: str = None
    allowedCmds: list = field(default_factory=lambda: ['update', 'setComm', 'setRover'])
    allowedValues: list = field(default_factory=lambda: [])

    def checkCmd(self, buffer: dict) -> None:
        try:
            command = [buffer['command']]
            command = list(set(command).intersection(self.allowedCmds))
            if command == []:
                logger.info(f'No valid command in api message for settings topic found. Allowed commands: {self.allowedCmds}. Aborting')
            else:
                self._performCmd(command[0], buffer)
        except Exception as e:
            logger.error('Api command for settings topic is invalid')
            logger.error(str(e))
    
    def _performCmd(self, command: str, buffer: dict) -> None:
        try:
            if command == 'update':
                self._createPayload()
            elif command == 'setComm':
                self._setComm(buffer)
            elif command == 'setRover':
                self._setRover(buffer)
        except Exception as e:
            logger.error('Api value for settings command is invalid')
            logger.error(str(e))
    
    def _createPayload(self) -> None:
        try:
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
            self.settingsstateJson = json.dumps(self.settingsstate)
        except Exception as e:
            logger.error('Could not create api settings payload.')
            logger.error(str(e))
    
    def _setComm(self, buffer: dict) -> None:
        try:
            value = buffer['value']
            for key in value:
                if key == 'robotConnectionType':
                    commcfg.use = value[key]
                if key == 'httpRobotIpAdress':
                    commcfg.http_ip = value[key]
                if key == 'httpRobotPassword':
                    commcfg.http_pass = value[key]
                if key == 'mqttClientId':
                    commcfg.mqtt_client_id = value[key]
                if key == 'mqttUser':
                    commcfg.mqtt_username = value[key]
                if key == 'mqttPassword':
                    commcfg.mqtt_pass = value[key]
                if key == 'mqttServer':
                    commcfg.mqtt_server = value[key]
                if key == 'mqttPort':
                    commcfg.mqtt_port = value[key]
                if key == 'mqttMowerNameWithPrefix':
                    commcfg.mqtt_mower_name = value[key]
                if key == 'uartPort':
                    commcfg.uart_port = value[key]
                if key == 'uartBaudrate':
                    commcfg.uart_baudrate = value[key]
                if key == 'apiType':
                    commcfg.api = value[key]
                if key == 'apiMqttClientId':
                    commcfg.api_mqtt_client_id = value[key]
                if key == 'apiMqttUser':
                    commcfg.api_mqtt_username = value[key]
                if key == 'apiMqttPassword':
                    commcfg.api_mqtt_pass = value[key]
                if key == 'apiMqttServer':
                    commcfg.api_mqtt_server = value[key]
                if key == 'apiMqttCassandraServerName':
                    commcfg.api_mqtt_cassandra_server_name = value[key]
                if key == 'apiMqttPort':
                    commcfg.api_mqtt_port = value[key]
                if key == 'messageServiceType':
                    if value[key] == 'telegram':
                        commcfg.message_service = 'Telegram'
                    elif value[key] == 'pushover':
                        commcfg.message_service = 'Pushover'
                    else:
                        commcfg.message_service = None
                if key == 'telegramApiToken':
                    commcfg.telegram_token = value[key]
                if key == 'telegramChatId':
                    commcfg.telegram_chat_id = value[key]
                if key == 'pushoverApiToken':
                    commcfg.pushover_token = value[key]
                if key == 'pushoverAppName':
                    commcfg.pushover_user = value[key]
            commcfg.save_commcfg()
        except Exception as e:
            logger.error('Api value for comm settings command is invalid')
            logger.error(str(e))
    
    def _setRover(self, buffer: dict) -> None:
        try:
            value = buffer['value'] 
            for key in value:
                if key == 'robotPositionMode':
                    rovercfg.positionmode = value[key]
                if key == 'longtitude':
                    rovercfg.lon = value[key]
                if key == 'latitude':
                    rovercfg.lat = value[key]
            rovercfg.save_rovercfg()
            robotInterface.performCmd('setPositionMode')
        except Exception as e:
            logger.error('Api value for rover settings command is invalid')
            logger.debug(str(e))


settingsTopic = SettingsTopic() 