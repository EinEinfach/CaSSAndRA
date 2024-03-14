import logging
logger = logging.getLogger(__name__)
import threading
from datetime import datetime
import time
import os

from . data import saveddata, calceddata, cleandata, cfgdata, logdata
from . data.scheduledata import schedule_tasks
from . comm.connections import mqttcomm, httpcomm, uartcomm, mqttapi
from . comm.api import cassandra_api
from . comm.messageservice import messageservice
from . data.roverdata import robot

restart = threading.Event()

#from data import saveddata
#from comm import mqttcomm, cmdlist, cmdtorover, comcfg

def message_service(restart: threading.ExceptHookArgs) -> None:
    while True:
        if restart.is_set():
            logger.info('Message service thread is stopped')
            return
        if robot.status == 'offline' and not messageservice.message_sent:
            messageservice.send_offline()
            messageservice.message_sent = True
        if robot.status == 'error' and not messageservice.message_sent:
            messageservice.send_error()
            messageservice.message_sent = True
        if robot.status != 'offline' and robot.status != 'error':
            messageservice.message_sent = False
        time.sleep(5)

def api(restart: threading.ExceptHookArgs) -> None:
    start_time_api = datetime.now()
    time_to_wait = 1
    while True:
        if restart.is_set():
            logger.info('API thread is stopped')
            mqttapi.disconnect()
            return
        if (datetime.now() - start_time_api).seconds >= 5*time_to_wait:
            logger.debug('Update api data')
            cassandra_api.update_payload()
            mqttapi.api_publish('status', cassandra_api.apistate)
            mqttapi.api_publish('robot', cassandra_api.robotstate_json)
            mqttapi.api_publish('maps', cassandra_api.mapsstate_json)
            mqttapi.api_publish('tasks', cassandra_api.tasksstate_json)
            mqttapi.api_publish('mow parameters', cassandra_api.mowparametersstate_json)
            mqttapi.api_publish('map', cassandra_api.mapstate_json)
            start_time_api = datetime.now()
        if mqttapi.buffer_api != []:
            cassandra_api.apistate = 'busy'
            mqttapi.api_publish('status', cassandra_api.apistate)
            cassandra_api.check_cmd(mqttapi.buffer_api[0])
            del mqttapi.buffer_api[0]
        time.sleep(1)

def schedule_loop(restart: threading.Event) -> None:
    while True:
        if restart.is_set():
            logger.info('Schedule thread is stopped')
            return
        schedule_tasks.check()
        time.sleep(60)

def store_data(restart: threading.Event, file_paths: tuple) -> None:
    start_time_save = datetime.now()
    time_to_wait = 1
    while True:
        if restart.is_set():
            logger.info('Data storage thread is stopped')
            logger.info('Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            return
        if (datetime.now() - start_time_save).seconds >= 1800*time_to_wait:
            logger.info('Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            start_time_save = datetime.now()
        time.sleep(1)

def connect_http(restart: threading.Event) -> None:
    start_time_state = datetime.now()
    start_time_obstacles = datetime.now()
    start_time_stats = datetime.now()
    time_to_wait = 1
    data_clean_finished = False
    time.sleep(2*time_to_wait)
    while True:
        if restart.is_set():
            logger.info('Connection thread is stopped')
            return
        elif httpcomm.http_status != 200:
            time.sleep(4)
            httpcomm.connect()
        else:
            if (datetime.now() - start_time_state).seconds > time_to_wait:
                httpcomm.get_state()
                start_time_state = datetime.now()
            if (datetime.now() - start_time_obstacles).seconds > 10*time_to_wait:
                httpcomm.get_obstacles()
                start_time_obstacles = datetime.now()
            if (datetime.now() - start_time_stats).seconds > 60*time_to_wait:
                httpcomm.get_stats()
                start_time_stats = datetime.now()
            httpcomm.cmd_to_rover()
            
        calceddata.calc_rover_state()
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def connect_mqtt(restart: threading.Event) -> None:
    data_clean_finished = False
    while True:
        if restart.is_set():
            logger.info('Connection thread is stopped')
            mqttcomm.disconnect()
            return
        
        mqttcomm.cmd_to_rover()
        calceddata.calc_rover_state()     
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def connect_uart(restart: threading.Event) -> None:
    start_time_state = datetime.now()
    start_time_obstacles = datetime.now()
    start_time_stats = datetime.now()
    time_to_wait = 1
    data_clean_finished = False
    time.sleep(2*time_to_wait)
    while True:
        if restart.is_set():
            uartcomm.client.close()
            logger.info('Connection thread is stopped')
            logger.info('Starting delay time')
            time.sleep(10)
            return
        if not uartcomm.uart_status:
            time.sleep(1)
            uartcomm.connect()
        else: 
            uartcomm.check_buffer()
            if (datetime.now() - start_time_state).seconds > time_to_wait:
                uartcomm.get_state()
                start_time_state = datetime.now()
            if (datetime.now() - start_time_obstacles).seconds > 10*time_to_wait:
                uartcomm.get_obstacles()
                start_time_obstacles = datetime.now()
            if (datetime.now() - start_time_stats).seconds > 60*time_to_wait:
                uartcomm.get_stats()
                start_time_stats = datetime.now()
            uartcomm.cmd_to_rover()
            
        calceddata.calc_rover_state()     
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def start(file_paths) -> None:
    logger.info('Backend: Starting backend server')
    logger.debug(f'Backend: Using {file_paths.data} for config and data storage')

    logger.info('Backend: Read communication config file')
    
    # todo: this should be refactored so the class is initialized with correct data immediately
    logdata.commlog.path = file_paths.log
    
    # initialize config data
    # todo: this should be a class or refactored in some way to avoid circular dependencies
    cfgdata.file_paths = file_paths
    connect_data = cfgdata.commcfg.read_commcfg()
    cfgdata.rovercfg.read_rovercfg()
    cfgdata.pathplannercfg.read_pathplannercfg()
    cfgdata.pathplannercfgstate.read_pathplannercfg()
    cfgdata.pathplannercfgtask.read_pathplannercfg()
    cfgdata.pathplannercfgtasktmp.read_pathplannercfg()
    cfgdata.pathplannercfgapi.read_pathplannercfg()
    cfgdata.appcfg.read_appcfg()
    cfgdata.schedulecfg.read_schedulecfg()
   
    # todo: saveddata should probably be a class instead
    saveddata.file_paths = file_paths
    logger.info('Backend: Read saved data')
    saveddata.read(file_paths.measure)
    logger.info('Backend: Read map data file')
    saveddata.read_perimeter(file_paths.map)
    logger.info('Backend: Read tasks data file')
    saveddata.read_tasks(file_paths.map)

    #read schedule tasks
    schedule_tasks.load_task_order(cfgdata.schedulecfg)

    if connect_data['USE'] == 'MQTT':
        logger.info('Selected connection MQTT')
        topics = {'TOPIC_STATE':'state', 'TOPIC_STATS':'stats','TOPIC_PROPS':'props','TOPIC_ONLINE':'online'}
        cfg = dict(CLIENT_ID=cfgdata.commcfg.mqtt_client_id, USERNAME=cfgdata.commcfg.mqtt_username, PASSWORD=cfgdata.commcfg.mqtt_pass,
                   MQTT_SERVER=cfgdata.commcfg.mqtt_server, PORT=cfgdata.commcfg.mqtt_port, NAME=cfgdata.commcfg.mqtt_mower_name)
        mqttcomm.create(cfg, topics)
        mqttcomm.connect()
        connection_start = datetime.now()
        while mqttcomm.client.connection_flag != True:
            time.sleep(0.1)
            if (datetime.now()-connection_start).seconds >10:
                break
        if mqttcomm.client.connection_flag:
            logger.info('Starting connection thread')
            connection_thread = threading.Thread(target=connect_mqtt, args=(restart,), name='connection')
            connection_thread.setDaemon(True)
            connection_thread.start()

            logger.info('Backend is successfully started')
        else:
            logger.info('Backend is running without communication to the rover')
        
    elif connect_data['USE'] == 'HTTP':
        logger.info('Selected connection HTTP')
        httpcomm.create()
        logger.info('Starting connection thread')
        connection_thread = threading.Thread(target=connect_http, args=(restart,), name='connection')
        connection_thread.setDaemon(True)
        connection_thread.start()
        logger.info('Backend is successfully started')
    
    elif connect_data['USE'] == 'UART':
        logger.info('Selected connection UART')
        uartcomm.create()
        logger.info('Starting connection thread')
        connection_thread = threading.Thread(target=connect_uart, args=(restart,), name='connection')
        connection_thread.setDaemon(True)
        connection_thread.start()
        logger.info('Backend is successfully started')
    else:
        logger.error('commcfg.json file is invalid')
    
    if connect_data['API'] != None:
        logger.info('Create API')
        if connect_data['API'] == 'MQTT':
            logger.info('Selected API is MQTT')
            topics = {'TOPIC_API_CMD':'api_cmd'}
            cfg = cfg = dict(CLIENT_ID=cfgdata.commcfg.api_mqtt_client_id, USERNAME=cfgdata.commcfg.api_mqtt_username, PASSWORD=cfgdata.commcfg.api_mqtt_pass,
                             MQTT_SERVER=cfgdata.commcfg.api_mqtt_server, PORT=cfgdata.commcfg.api_mqtt_port, NAME=cfgdata.commcfg.api_mqtt_cassandra_server_name)
            mqttapi.create(cfg, topics)
            mqttapi.client.will_set(mqttapi.mqtt_mower_name+'/status', payload='offline')
            mqttapi.connect()
            connection_start = datetime.now()
            while mqttapi.client.connection_flag != True:
                time.sleep(0.1)
                if (datetime.now()-connection_start).seconds >10:
                    break
            if mqttapi.client.connection_flag:
                mqttapi.client.publish(cfgdata.commcfg.api_mqtt_cassandra_server_name+'/status', 'boot')
                logger.info('Starting API thread')
                api_thread = threading.Thread(target=api, args=(restart,), name='api')
                api_thread.setDaemon(True)
                api_thread.start()
                logger.info('API successful created')
    
    if cfgdata.commcfg.message_service != None:
        if cfgdata.commcfg.message_service == 'Telegram':
            messageservice.telegram_token = cfgdata.commcfg.telegram_token
            logger.info('Message service is telegram, check for chat id')
            message_service_connection = messageservice.get_chat_id()
            if message_service_connection == 0:
                message_servive_thread = threading.Thread(target=message_service, args=(restart,), name='message service')
                message_servive_thread.setDaemon(True)
                message_servive_thread.start()
                logger.info('Message service is successful started')
            else:
                logger.warning('Message service could not be started. Check your message service settings.')
                logger.debug(f'Error code: {message_service_connection}')
                
        if cfgdata.commcfg.message_service == 'Pushover':
            messageservice.pushover_token = cfgdata.commcfg.pushover_token
            messageservice.pushover_user = cfgdata.commcfg.pushover_user
            message_servive_thread = threading.Thread(target=message_service, args=(restart,), name='message service')
            message_servive_thread.setDaemon(True)
            message_servive_thread.start()
            logger.info('Message service is successful started')
            
    #start an own thread for data storing
    logger.info('Starting thread for data storage')
    datastorage_thread = threading.Thread(target=store_data, args=(restart, file_paths), name='data storage')
    datastorage_thread.setDaemon(True)
    datastorage_thread.start()

    #start an own thread for schedule
    logger.info('Starting schedule thread')
    schedule_thread = threading.Thread(target=schedule_loop, args=(restart,), name='schedule_loop')
    schedule_thread.setDaemon(True)
    schedule_thread.start()

    #give some times to establish connection
    time.sleep(2)

def reboot() -> None:
    logger.info('Backendserver is being restarted')
    restart.set()
    data_storage_running = True
    while data_storage_running:
        data_storage_running = False
        for th in threading.enumerate():
            if th.name == 'data storage':
                data_storage_running = True
    time.sleep(5)
    restart.clear()
    start(cfgdata.file_paths)

def stop() -> None:
    logger.info('Backendserver is being shut down')
    restart.set()
    data_storage_running = True
    while data_storage_running:
        data_storage_running = False
        for th in threading.enumerate():
            if th.name == 'data storage':
                data_storage_running = True
    restart.clear()

def shutdown() -> None:
    if cfgdata.commcfg.use == 'UART':
        logger.info('OS will shut down.')
        os.system('sudo shutdown now')