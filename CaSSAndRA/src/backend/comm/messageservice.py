import logging
logger = logging.getLogger(__name__)

import requests
from dataclasses import dataclass
import json

from .. data.roverdata import robot
from .. data.cfgdata import commcfg

from icecream import ic

@dataclass
class MessageService:
    telegram_token: str = None
    pushover_token: str = None
    chat_id: str = None
    message_sent: bool = False
    pushover_user: str = None

    def get_chat_id(self) -> int:
        try:
            if commcfg.telegram_chat_id == None:
                logger.info('Telegram api request for chat id')
                url = f'https://api.telegram.org/bot{self.telegram_token}/getUpdates'
                result = requests.get(url).json()
                if 'ok' in result and not 'error_code' in result:
                    self.chat_id = result['result'][0]['message']['chat']['id']
                    commcfg.telegram_chat_id = self.chat_id
                    commcfg.save_commcfg()
                    return 0
                else:
                    return result['error code']
            else:
                logger.info('Chat id is already known. Use chat id from commcfg.json')
                self.chat_id = commcfg.telegram_chat_id
                return 0
        except Exception as e:
            logger.warning('Did not get chat id via telegram api. Message service not active')
            logger.debug(f'{e}')
            return -1
    
    def send_offline(self) -> None:
        message='Attention! Robot is offline'
        self.send_over_api(message) 
    
    def send_error(self) -> None:
        message='Attention! Robot reports an error: '
        message = message+robot.sensor_status
        self.send_over_api(message)
    
    def send_message(self, message: str) -> None:
        self.send_over_api(message)
    
    def send_over_api(self, message: str) -> None:
        if commcfg.message_service == 'Telegram':
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage?chat_id={self.chat_id}&text={message}"
            try:
                result = requests.get(url).json()
                if 'ok' in result:
                    logger.info(f'Message: {message} was send to operator')
            except Exception as e:
                logger.info('Message could not send to operator')
                logger.debug(f'{e}')
        elif commcfg.message_service == 'Pushover':
            url = f"https://api.pushover.net/1/messages.json"
            header = {"Content-Type": "application/json"}
            body = json.dumps({"token": self.pushover_token, "user": self.pushover_user, "title": "CaSSAndRA", "message": message})
            try:
                result = requests.post(url=url, headers=header, data=body, timeout=6)
                if result.ok:
                    logger.info(f'Message: {message} was send to operator')
                else:
                    logger.info('Message could not send to operator')
            except Exception as e:
                logger.info('Message could not send to operator')
                logger.debug(f'{e}')

messageservice = MessageService()
