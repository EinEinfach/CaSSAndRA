import logging
logger = logging.getLogger(__name__)
import threading
from datetime import datetime
import time
import os

from . data import saveddata, calceddata, cleandata, cfgdata, logdata
from .comm.connections import mqttcomm, httpcomm, uartcomm

restart = threading.Event()

#from data import saveddata
#from comm import mqttcomm, cmdlist, cmdtorover, comcfg

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
                uartcomm.get_stats()
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
    cfgdata.appcfg.read_appcfg()

    # todo: saveddata should probably be a class instead
    saveddata.file_paths = file_paths
    logger.info('Backend: Read saved data')
    saveddata.read(file_paths.measure)
    logger.info('Backend: Read map data file')
    saveddata.read_perimeter(file_paths.map)
    logger.info('Backend: Read tasks data file')
    saveddata.read_tasks(file_paths.map)

    if connect_data['USE'] == 'MQTT':
        logger.info('Selected connection MQTT')
        mqttcomm.create()
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
    
    #start an own thread for data storing
    logger.info('Starting thread for data storage')
    datastorage_thread = threading.Thread(target=store_data, args=(restart, file_paths), name='data storage')
    datastorage_thread.setDaemon(True)
    datastorage_thread.start()

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