import logging
logger = logging.getLogger(__name__)

import time
import json
import paho.mqtt.client as mqtt
import pandas as pd
import random

from src.backend.data import datatodf, roverdata, mapdata
from . import cmdtorover, cmdlist, message

def cmd_to_rover(client, connect_data) -> None:
    topic = connect_data['MQTT'][5]['MOWER_NAME']+'/command'
    msg_pckg = message.check() 

    for i, msg in msg_pckg.iterrows():   
        publish(client, topic, msg_pckg['msg'][i])    
    time.sleep(0.1)
    
        
   
def connect_mqtt(connect_data: dict()) -> mqtt:
    client_id = connect_data['MQTT'][0]['CLIENT_ID'] + str(random.randint(1, 1000))
    username = connect_data['MQTT'][1]['USERNAME'] 
    password = connect_data['MQTT'][2]['PASSWORD']
    mqtt_server = connect_data['MQTT'][3]['MQTT_SERVER']
    port = connect_data['MQTT'][4]['PORT']
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info('Backend: Subscriptions to the rover MQTT topics succsessfull')
        else:
            client.connection_flag = False
            logger.warning('Backend: MQTT connection to the rover lost. Code: '+str(rc))
                    
    # Set Connecting Client ID
    client = mqtt.Client(client_id)
    client.connection_flag = False
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    try:
        client.connect(mqtt_server, port)
        client.connection_flag = True
        logger.info('Backend: Connection to the MQTT-Server succsessfull')
    except:
        logger.warning('Backend: Connection to the MQTT-Server failed')

    return client
   

def subscribe(client: mqtt, connect_data: dict()):
    mower_name = connect_data['MQTT'][5]['MOWER_NAME']
    topics = {
            'TOPIC_STATE':'state', 
            'TOPIC_STATS':'stats',
            'TOPIC_PROPS':'props',
            'TOPIC_ONLINE':'online'
        }
    def on_message(client, userdata, msg):
        logger.info('Backend: RX topic:'+msg.topic+' message:'+str(msg.payload))
        if msg.topic == mower_name+'/'+topics['TOPIC_STATE']:
            decoded_message = str(msg.payload.decode('utf-8'))
            data = json.loads(decoded_message)
            datatodf.add_state_to_df_from_mqtt(data)
        elif msg.topic == mower_name+'/'+topics['TOPIC_PROPS']:
            decoded_message = str(msg.payload.decode('utf-8'))
            data = json.loads(decoded_message)
            datatodf.add_props_to_df_from_mqtt(data)
        elif msg.topic == mower_name+'/'+topics['TOPIC_STATS']:
            decoded_message = str(msg.payload.decode('utf-8'))
            data = json.loads(decoded_message)
            datatodf.add_stats_to_df_from_mqtt(data)
        elif msg.topic == mower_name+'/'+topics['TOPIC_ONLINE']:
            data = msg.payload.decode('utf-8')
            datatodf.add_online_to_df_from_mqtt(data)

            
    client.subscribe(mower_name+'/'+topics['TOPIC_STATE'])
    client.subscribe(mower_name+'/'+topics['TOPIC_STATS'])
    client.subscribe(mower_name+'/'+topics['TOPIC_PROPS'])
    client.subscribe(mower_name+'/'+topics['TOPIC_ONLINE'])
    client.on_message = on_message

def publish(client: mqtt, topic: str(), msg: str()):
    result = client.publish(topic, msg)
    status = result[0]
    if status == 0:
        logger.info('Backend: TX publish: '+topic+' with message: '+msg)
    else:
        logger.warning('Backend: MQTT failed to publish: '+topic+' with message: '+msg)
    

def start_mqtt(client: mqtt, connect_data: dict()):
    logger.debug('Backend: Starting MQTT client loop')
    client.loop_start()
    #while True:
        #cmd_to_rover(client, connect_data)
    #client.loop_forever()



