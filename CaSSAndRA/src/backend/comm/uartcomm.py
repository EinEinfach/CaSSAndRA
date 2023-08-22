import logging
logger = logging.getLogger(__name__)

import serial
import time

from src.backend.comm import message
from src.backend.data import datatodf

def cmd_to_rover(ser: serial) -> bool:
    msg_pckg = message.check()
    try:
        for i, msg in msg_pckg.iterrows(): 
            uart_msg = msg_pckg['msg'][i] + ',\n'
            ser.write(bytes(uart_msg,'UTF-8'))  
            logger.debug('UART send message: '+msg_pckg['msg'][i])
            logger.debug(str(bytes(uart_msg,'UTF-8')))
            time.sleep(0.1)
        return True
    
    except Exception as e:
        logger.warning('Backend: Could not send data to the rover')
        logger.debug(str(e))
        return False
            
def connect_uart(connect_data: dict()) -> list():
    try:
        ser = serial.Serial(connect_data['UART'][0]['SERPORT'], connect_data['UART'][1]['BAUDRATE'], timeout=3)
        ser.reset_input_buffer()
        logger.info('Backend: UART Connection successfull')
        return ser, ser.is_open
    except:
        logger.warning('Backend: UART Connection to the rover is not possible.')
        return -1, False

def on_state(data: str()):
    datatodf.add_state_to_df(data)

def on_stats(data: str()):
    datatodf.add_stats_to_df(data)

