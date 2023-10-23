import logging
logger = logging.getLogger(__name__)

import requests
from dataclasses import dataclass

from .. data.roverdata import robot

from icecream import ic

@dataclass
class TelegramMessageService:
    token: str = None
    chat_id: str = None
    message_sent: bool = False

    def get_chat_id(self) -> int:
        try:
            logger.info('Telegram api request for chat id')
            url = f'https://api.telegram.org/bot{self.token}/getUpdates'
            result = requests.get(url).json()
            if 'ok' in result and not 'error_code' in result:
                self.chat_id = result['result'][0]['message']['chat']['id']
                return 0
            else:
                return result['error code']
        except Exception as e:
            logger.warning('Did not get chat id via telegram api. Message service not active')
            logger.debug(f'{e}')
            ic(e)
            return -1
    
    def send_offline(self) -> None:
        message='Attention! Robot is offline'
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={message}"
        try:
            result = requests.get(url).json()
            if 'ok' in result:
                logger.info(f'Message: {message} was send to operator')
        except Exception as e:
            logger.info('Message could not send to operator')
            logger.debug(f'{e}')
    
    def send_error(self) -> None:
        message='Attention! Robot reports an error: '
        message = message+robot.sensor_status
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={message}"
        try:
            result = requests.get(url).json()
            if 'ok' in result:
                logger.info(f'Message: {message} was send to operator')
        except Exception as e:
            logger.info('Message could not send to operator')
            logger.debug(f'{e}')
    
    def send_message(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage?chat_id={self.chat_id}&text={message}"
        try:
            result = requests.get(url).json()
            if 'ok' in result:
                logger.info(f'Message: {message} was send to operator')
        except Exception as e:
            logger.info('Message could not send to operator')
            logger.debug(f'{e}')


telegram = TelegramMessageService()
