import logging
logger = logging.getLogger(__name__)

#package imports
import time
import json
import paho.mqtt.client as mqtt
import requests
import serial
import random
from dataclasses import dataclass, field
from datetime import datetime

#local imports
from .. data import datatodf
from .. data.cfgdata import CommCfg, commcfg
from . import message

@dataclass
class MQTT:
    client: mqtt.Client = None
    mqtt_client_id: str = None
    mqtt_username: str = None
    mqtt_pass: int = None
    mqtt_server: str = None
    mqtt_port: int = None
    mqtt_mower_name: str = None
    mqtt_topics: dict = field(default_factory=dict)
    sub_ids: dict = field(default_factory=dict)
    buffer_api: list = field(default_factory=list)

    def create(self, cfg: dict, topics: dict) -> None:
        self.mqtt_client_id = cfg['CLIENT_ID']
        self.mqtt_username = cfg['USERNAME']
        self.mqtt_pass = cfg['PASSWORD']
        self.mqtt_server = cfg['MQTT_SERVER']
        self.mqtt_port = cfg['PORT']
        self.mqtt_mower_name = cfg['NAME']
        self.mqtt_topics = topics
        self.client = mqtt.Client(self.mqtt_client_id + str(random.randint(1, 1000)))
        self.client.connection_flag = False
        self.client.username_pw_set(self.mqtt_username, self.mqtt_pass)
    
    def disconnect(self) -> None:
        logger.info('Disconnecting')
        self.client.disconnect()
    
    def connect(self) -> None:
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        try:
            self.client.connect(self.mqtt_server, self.mqtt_port, keepalive=60)
            logger.info('Connecting...')
        except Exception as e:
            logger.warning('Connection to the MQTT server failed')
            logger.debug(str(e))
        self.client.loop_start()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info('Connection to the MQTT server successful')  
            client.connection_flag = True
            self.subscribe()
        else:
            logger.warning('Connection to the MQTT server not possible')
            client.connection_flag = False
    
    def on_disconnect(self, client, userdata, rc):
        logger.warning('MQTT connection lost, reconnecting...')
        logger.info(f"Disconnecting reason: {rc}")
        self.client.connection_flag = False
    
    def on_message(self, client, userdata, msg):
        logger.info('RX:'+msg.topic+' message:'+str(msg.payload))
        if 'TOPIC_STATE' in self.mqtt_topics and msg.topic == self.mqtt_mower_name+'/'+self.mqtt_topics['TOPIC_STATE']:
            decoded_message = str(msg.payload.decode('utf-8'))
            data = json.loads(decoded_message)
            datatodf.add_state_to_df_from_mqtt(data)
        elif 'TOPIC_PROPS' in self.mqtt_topics and msg.topic == self.mqtt_mower_name+'/'+self.mqtt_topics['TOPIC_PROPS']:
            decoded_message = str(msg.payload.decode('utf-8'))
            data = json.loads(decoded_message)
            datatodf.add_props_to_df_from_mqtt(data)
        elif 'TOPIC_STATS' in self.mqtt_topics and msg.topic == self.mqtt_mower_name+'/'+self.mqtt_topics['TOPIC_STATS']:
            decoded_message = str(msg.payload.decode('utf-8'))
            data = json.loads(decoded_message)
            datatodf.add_stats_to_df_from_mqtt(data)
        elif 'TOPIC_ONLINE' in self.mqtt_topics and msg.topic == self.mqtt_mower_name+'/'+self.mqtt_topics['TOPIC_ONLINE']:
            data = msg.payload.decode('utf-8')
            datatodf.add_online_to_df_from_mqtt(data)
        elif 'TOPIC_API_CMD' in self.mqtt_topics and msg.topic == self.mqtt_mower_name+'/'+self.mqtt_topics['TOPIC_API_CMD']:
            data = msg.payload.decode('utf-8')
            try:
                logger.info(f'Got message over api: {data}')
                data = json.loads(data)
                self.buffer_api.append(data)
            except Exception as e:
                logger.warning('Message content is not valid json format')
                logger.debug(str(e))
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        if mid in self.sub_ids.keys():
            logger.info(f'Subscribed to {self.sub_ids[mid]}')
        else:
            logger.warning(f'Subscription failed')
    
    def subscribe(self) -> None:
        self.client.on_subscribe = self.on_subscribe
        mower_name = self.mqtt_mower_name
        topics = self.mqtt_topics
        for topic in topics:
            resp, mid = self.client.subscribe(mower_name+'/'+topics[topic])
            self.sub_ids[mid] = mower_name+'/'+topics[topic]
        self.client.on_message = self.on_message
    
    def cmd_to_rover(self) -> None:
        topic = self.mqtt_mower_name+'/command'
        msg_pckg = message.check() 
        for i, msg in msg_pckg.iterrows():   
            result = self.client.publish(topic, msg_pckg['msg'][i]) 
            status = result[0]
            if status == 0:
                logger.info('TX: '+topic+' with message: '+msg_pckg['msg'][i])
            else:
                logger.warning('Failed to publish: '+topic+' with message: '+msg_pckg['msg'][i])   
            time.sleep(0.1)
    
    def api_publish(self, topic, payload) -> None:
        topic = self.mqtt_mower_name+'/'+topic
        result = self.client.publish(topic, payload)
        if result[0] == 0:
            logger.debug('API TX: '+topic+' '+payload)
        else:
            logger.warning('API failed to publish: '+topic+'with message: '+payload)
@dataclass
class HTTP:
    http_ip: str = None
    http_pass: int = None
    header = {"Content-Type": "text/plain"}
    http_status: int = -1
    http_encryption: int = 0
    http_encryptchallenge: int = 0
    http_encryptkey: int = None

    def create(self) -> None:
        self.http_ip = commcfg.http_ip
        self.http_pass = commcfg.http_pass
        self.connect()
    
    def connect(self):
        logger.info('Connecting...')
        try:
            data = self.reqandchecksum('AT+V')
            logger.info('TX: '+data)
            res = requests.post(url=self.http_ip, headers=self.header, data=data+'\n', timeout=6)
            logger.debug('Status code: '+str(res.status_code))
            logger.info('RX: '+res.text)
            if res.status_code == 200 and 'V,' in res.text and res.text[0] == 'V':
                reslist = res.text.split(',')
                encrypt = int(reslist[3])
                encryptchallenge = int(reslist[4])
                datatodf.add_props_to_df_from_http(res.text)
                datatodf.add_online_to_df_from_http(True)
                self.http_status = res.status_code
                self.http_encryption = encrypt
                self.http_encryptchallenge = encryptchallenge
                if self.http_encryption == 1:
                    logger.debug('Encryption: true')
                    try:
                        self.http_encryptkey = int(self.http_pass)%int(self.http_encryptchallenge)
                    except Exception as e:
                        logger.warning('Password is invalid. Check your comm config')
                        logger.debug(str(e))
                        self.http_encryptkey = None
                        self.http_status = -1
            else:
                logger.warning('Http request for props delivered implausible string')
                datatodf.add_online_to_df_from_http(False)
                self.http_status = -1
                self.http_encryption = 0
                self.http_encryptchallenge = 0
        except requests.exceptions.RequestException as e: 
            logger.warning('HTTP-Connection to the rover lost or not possible. Trying to reconnect')
            logger.debug(str(e))
            datatodf.add_online_to_df_from_http(False)
            self.http_status = -1
            self.http_encryption = 0
            self.http_encryptchallenge = 0
    
    def get_state(self) -> None:
        logger.info('Performing get state http-request')
        data = self.reqandchecksum('AT+S')
        if self.http_encryption == 1:
            data_ascii = [ord(c) for c in data]
            data_encrypt = [x + self.http_encryptkey for x in data_ascii]
            data_encrypt = [x - 126 + 31 if x>=126 else x for x in data_encrypt]
            data = ''.join(map(chr, data_encrypt))
        try:
            logger.info('TX: '+data) 
            res = requests.post(url=self.http_ip, headers=self.header, data=data+'\n', timeout=6)
            logger.debug('Status code: '+str(res.status_code))
            logger.info('RX: '+res.text)
            if len(res.text) == 0:
                logger.warning('HTTP request for state delivered implausible string')
                self.http_status = -1
            elif res.status_code == 200 and self.checkchecksum(res.text) and len(res.text) > 20:
                datatodf.add_state_to_df(res.text)
                self.http_status = res.status_code
            else:
                logger.warning('HTTP request for state delivered implausible string')
                self.http_status = -1
        except requests.exceptions.RequestException as e: 
            logger.warning('HTTP-Connection to the rover lost or not possible. Trying to reconnect')
            logger.debug(str(e))
            self.http_status = -1
    
    def get_stats(self) -> None:
        logger.info('Performing get stats http-request')
        data = self.reqandchecksum('AT+T')
        if self.http_encryption == 1:
            data_ascii = [ord(c) for c in data]
            data_encrypt = [x + self.http_encryptkey for x in data_ascii]
            data_encrypt = [x - 126 + 31 if x>=126 else x for x in data_encrypt]
            data = ''.join(map(chr, data_encrypt))
        try:
            logger.info('TX: '+data)
            res = requests.post(url=self.http_ip, headers=self.header, data=data+'\n', timeout=6)
            logger.debug('Status code: '+str(res.status_code))
            logger.info('RX: '+res.text)
            if len(res.text) == 0:
                logger.warning('HTTP request for state delivered implausible string')
                self.http_status = -1
            elif res.status_code == 200 and self.checkchecksum(res.text) and len(res.text) > 20:
                datatodf.add_stats_to_df(res.text)
                self.http_status = res.status_code
            else:
                logger.warning('Http request for stats delivered implausible string')
                self.http_status = -1  
        except requests.exceptions.RequestException as e: 
            logger.warning('Backend: HTTP-Connection to the rover lost or not possible. Trying to reconnect')
            logger.debug(str(e))
            self.http_status = -1
        
    def get_obstacles(self) -> int:
        logger.info('Performing get obstacles http-request')
        data = self.reqandchecksum('AT+S2')
        if self.http_encryption == 1:
            data_ascii = [ord(c) for c in data]
            data_encrypt = [x + self.http_encryptkey for x in data_ascii]
            data_encrypt = [x - 126 + 31 if x>=126 else x for x in data_encrypt]
            data = ''.join(map(chr, data_encrypt))
        try:
            logger.info('Backend: TX '+data) 
            res = requests.post(url=self.http_ip, headers=self.header, data=data+'\n', timeout=6)
            logger.debug('Status code: '+str(res.status_code))
            logger.info('Backend: RX '+res.text)
            if len(res.text) == 0:
                logger.warning('Backend: HTTP request for obstacles delivered implausible string')
                self.http_status = -1
            elif res.status_code == 200 and self.checkchecksum(res.text) and len(res.text) > 8:
                datatodf.add_obstacles_to_df(res.text)
                self.http_status = res.status_code
            else:
                logger.warning('Backend: HTTP request for obstacles delivered implausible string')
                self.http_status = -1
        except requests.exceptions.RequestException as e: 
            logger.warning('Backend: HTTP-Connection to the rover lost or not possible. Trying to reconnect')
            logger.debug(str(e))
            self.http_status = -1
    
    def cmd_to_rover(self) -> None:
        msg_pckg = message.check()
        if self.http_status != 200:
            return
        for i, msg in msg_pckg.iterrows():   
            rep_cnt = 0
            logger.debug(''+msg_pckg['msg'][i]+' will be send to the rover')
            data = self.reqandchecksum(msg_pckg['msg'][i])
            if self.http_encryption == 1:
                data_ascii = [ord(c) for c in data]
                data_encrypt = [x + self.http_encryptkey for x in data_ascii]
                data_encrypt = [x - 126 + 31 if x>126 else x for x in data_encrypt]
                data = ''.join(map(chr, data_encrypt))  
            try:
                logger.info('TX '+data)
                res = requests.post(url=self.http_ip, headers=self.header, data=data+'\n', timeout=6)
                logger.info('RX: '+res.text)
                self.http_status = res.status_code    
                while self.http_status != 200:
                    rep_cnt += 1
                    res = requests.post(url=self.http_ip, headers=self.header, data=data+'\n', timeout=6)
                    self.http_status = res.status_code 
                    if rep_cnt > 30:
                        logger.warning('Failed send the message to the rover')
                    time.sleep(1) 
            except requests.exceptions.RequestException as e:
                logger.warning('HTTP-Connection to the rover lost or not possible. Trying to reconnect')
                logger.debug(str(e))
            time.sleep(0.1)
            
    def reqandchecksum(self, req: str) -> str:
        res = hex(sum(req.encode('ascii')) % 256)
        logger.debug('Calced checksumme: '+res)
        res = req+','+res
        return res  
    
    def checkchecksum(self, res: str) -> bool:
        try:
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
        except Exception as e:
            logger.warning('Could not calculate checksum.')
            logger.debug(str(e))
            return False

@dataclass
class UART:
    client: serial.Serial = serial.Serial()
    uart_port: str = None
    uart_baudrate: int = None
    uart_status: bool = None
    
    def create(self) -> None:
        self.uart_port = commcfg.uart_port
        self.uart_baudrate = commcfg.uart_baudrate
        self.connect()
        self.get_state_time = datetime.now()
        self.get_stats_time = datetime.now()
        self.get_obstacles_time = datetime.now()
    
    def connect(self) -> None:
        try:
            logger.info('Connecting...')
            self.client = serial.Serial(self.uart_port, self.uart_baudrate, timeout=3)
            self.client.reset_input_buffer()
            self.uart_status = True
            logger.info('Connection successful')
        except:
            self.uart_status = False
            logger.warning('Connection to the rover is not possible.')
    
    def check_buffer(self) -> None:
        try: 
            if self.client.in_waiting > 0:
                data = self.client.readline().decode('utf-8').rstrip()
                logger.info('RX: '+data)
                if data.find('S,') == 0:
                    self.on_state(data)
                if data.find('T,') == 0:
                    self.on_stats(data) 
                if data.find('S2,') == 0:
                    self.on_obstacle(data)
        except Exception as e:
            logger.warning('Exception in communication occured, trying to reconnect')
            logger.debug(str(e))
            self.client.close()
            self.uart_status = False   
    
    def get_state(self) -> None:
        if self.uart_status:
            msg_pckg = 'AT+S\n'
            self.client.write(bytes(msg_pckg, 'UTF-8'))
            logger.info('TX: '+str(bytes(msg_pckg, 'UTF-8')))

    def get_stats(self) -> None:
        if self.uart_status:
            msg_pckg = 'AT+T\n'
            self.client.write(bytes(msg_pckg, 'UTF-8'))
            logger.info('TX: '+str(bytes(msg_pckg, 'UTF-8'))) 
                  
    def get_obstacles(self) -> None:
        if self.uart_status:
            msg_pckg = 'AT+S2\n'
            self.client.write(bytes(msg_pckg, 'UTF-8'))
            logger.info('TX: '+str(bytes(msg_pckg, 'UTF-8')))
    
    def cmd_to_rover(self) -> None:
        msg_pckg = message.check()
        try:
            for i, msg in msg_pckg.iterrows(): 
                uart_msg = msg_pckg['msg'][i] + ',\n'
                logger.debug(msg_pckg['msg'][i]+' will be send to rover')
                self.client.write(bytes(uart_msg,'UTF-8'))  
                logger.info('TX: '+str(bytes(uart_msg,'UTF-8')))
                time.sleep(0.1)
        except Exception as e:
            logger.warning('Could not send data to the rover')
            logger.debug(str(e))
            self.uart_status = False
    
    def on_state(self, data: str) -> None:
        datatodf.add_state_to_df(data)

    def on_stats(self, data: str) -> None:
        datatodf.add_stats_to_df(data)

    def on_obstacle(self, data: str) -> None:
        datatodf.add_obstacles_to_df(data)
    
#Create connection instances
mqttcomm = MQTT()
httpcomm = HTTP()
uartcomm = UART()

#Create api instance
mqttapi = MQTT()

        
    

