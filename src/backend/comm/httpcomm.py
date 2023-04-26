import logging
logger = logging.getLogger(__name__)

import json
import requests
import time
import pandas as pd

from src.backend.data import datatodf, roverdata
from . import cmdtorover, cmdlist, message

Headers = {"Content-Type": "text/plain"}

def checkchecksum(res: str()) -> bool:
    res_splited = res.split(',')
    check_sum = res_splited[-1]
    res = res.replace(','+check_sum, '')
    check_sum = hex(int(check_sum, 16))
    calced_check_sum = hex(sum(res.encode('ascii')) % 256)
    logger.debug('Recieved checksum:'+str(check_sum)+' Calced checksum: '+str(calced_check_sum))
    if calced_check_sum == check_sum:
        return True
    else:
        return False

def reqandchecksum(req: str()) -> str():
    res = hex(sum(req.encode('ascii')) % 256)
    logger.debug('Calced checksumme: '+res)
    res = req+','+res
    return res  

def cmd_to_rover(connect_data: dict(), connection: list()):#, msg_pckg: pd.DataFrame()) -> int():
    msg_pckg = message.check()
    connection_status = 200
    if connection[1] == 1:
        try:
            encryptkey = int(connect_data['HTTP'][1]['PASSWORD'])%int(connection[2])
        except:
            logger.warning('Backend: Valid password not found. Check your comm config')
            encryptkey = 0

    for i, msg in msg_pckg.iterrows():   
        rep_cnt = 0
        logger.debug('Backend: '+msg_pckg['msg'][i]+' is send to the rover')
        data = reqandchecksum(msg_pckg['msg'][i])
        if connection[1] == 1:
            logger.debug('encryption true')
            data_ascii = [ord(c) for c in data]
            data_encrypt = [x + encryptkey for x in data_ascii]
            data_encrypt = [x - 126 + 31 if x>=126 else x for x in data_encrypt]
            data = ''.join(map(chr, data_encrypt))  

        res = requests.post(url=connect_data['HTTP'][0]['IP'], headers=Headers, data=data+'\n', timeout=2)
        connection_status = res.status_code    
        while connection_status != 200:
            rep_cnt += 1
            res = requests.post(url=connect_data['HTTP'][0]['IP'], headers=Headers, data=data+'\n', timeout=2)
            connection_status = res.status_code 
            if rep_cnt > 30:
                logger.warning('Backend: Failed send the message to the rover')
                return connection_status 
            time.sleep(1)  
    return connection_status

def connect_http(connect_data: dict()) -> list:
    logger.info('Backend: Try initial HTTP request')
    try:
        res = requests.post(url=connect_data['HTTP'][0]['IP'], headers=Headers, data=reqandchecksum('AT+V')+'\n', timeout=2)
        logger.debug('Status code: '+str(res.status_code))
        logger.debug('Content: '+res.text)
        if res.status_code == 200 and 'V,' in res.text:
            reslist = res.text.split(',')
            encrypt = int(reslist[3])
            encryptchallenge = int(reslist[4])
            datatodf.add_props_to_df_from_http(res.text)
            datatodf.add_online_to_df_from_http(True)
            return [res.status_code, encrypt, encryptchallenge]
        else:
            logger.warning('Backend: Http request for props delivered implausible string')
            datatodf.add_online_to_df_from_http(False)
            return [-1, 0, 0]
    except requests.exceptions.RequestException as e: 
        logger.warning('Backend: HTTP-Connection to the rover lost or not possible. Trying to reconnect')
        datatodf.add_online_to_df_from_http(False)
        return [-1, 0, 0]

def get_state(connect_data: dict(), connection: list()) -> int:
    logger.info('Backend: Performing get state http-request')
    data = reqandchecksum('AT+S')
    if connection[1] == 1:
        logger.debug('encryption true')
        try:
            encryptkey = int(connect_data['HTTP'][1]['PASSWORD'])%int(connection[2])
        except:
            logger.warning('Backend: Valid password not found. Check your comm config')
            encryptkey = 0
        data_ascii = [ord(c) for c in data]
        data_encrypt = [x + encryptkey for x in data_ascii]
        data_encrypt = [x - 126 + 31 if x>=126 else x for x in data_encrypt]
        data = ''.join(map(chr, data_encrypt))

    try: 
        res = requests.post(url=connect_data['HTTP'][0]['IP'], headers=Headers, data=data+'\n', timeout=2)
        logger.debug('Status code: '+str(res.status_code))
        logger.debug('Content: '+res.text)
        if res.status_code == 200 and checkchecksum(res.text) and len(res.text) > 20:
            datatodf.add_state_to_df(res.text)
            return res.status_code
        else:
            logger.warning('Backend: HTTP request for state delivered implausible string')
            return -1
    except requests.exceptions.RequestException as e: 
        logger.warning('Backend: HTTP-Connection to the rover lost or not possible. Trying to reconnect')
        return -1

def get_stats(connect_data: dict(), connection: list()) -> int:
    logger.info('Backend: Performing get stats http-request')
    data = reqandchecksum('AT+T')
    if connection[1] == 1:
        logger.debug('encryption true')
        try:
            encryptkey = int(connect_data['HTTP'][1]['PASSWORD'])%int(connection[2])
        except:
            logger.warning('Backend: Valid password not found. Check your comm config')
            encryptkey = 0
        data_ascii = [ord(c) for c in data]
        data_encrypt = [x + encryptkey for x in data_ascii]
        data_encrypt = [x - 126 + 31 if x>=126 else x for x in data_encrypt]
        data = ''.join(map(chr, data_encrypt))

    try:
        res = requests.post(url=connect_data['HTTP'][0]['IP'], headers=Headers, data=data+'\n', timeout=2)
        logger.debug('Status code: '+str(res.status_code))
        logger.debug('Content: '+res.text)
        if res.status_code == 200 and checkchecksum(res.text) and len(res.text) > 20:
            datatodf.add_stats_to_df(res.text)
            return res.status_code
        else:
            logger.warning('Backend: Http request for stats delivered implausible string')
            return -1
        
    except requests.exceptions.RequestException as e: 
        logger.warning('Backend: HTTP-Connection to the rover lost or not possible. Trying to reconnect')
        return -1

# def start_http(connect_data: dict(), connection_status: int):
#     stats_couter = 0
#     state_counter = 0
#     last_call_move = False
#     while True:
#         if connection_status != 200:
#             connection_status = connect_http(connect_data)
#         else:
#             #Get state data
#             if state_counter == 10:
#                 connection_status = get_state(connect_data)
#                 state_counter = 0

#             #Get stats data
#             if stats_couter == 150:
#                 connection_status = get_stats(connect_data)
#                 stats_couter = 0
#             state_counter += 1
#             stats_couter += 1

#             #Send commands to rover if there
#             #msg_pckg = message.check() 
#             connection_status = cmd_to_rover(connect_data)#, msg_pckg)

#             time.sleep(0.4)

# if __name__ == '__main__':
#     connect_data = {"HTTP":
#     [
#         {"IP": "http://192.168.2.55"},
#         {"PASSWORD": ""}
#     ]
# }
#     connection_status = connect_http(connect_data)
