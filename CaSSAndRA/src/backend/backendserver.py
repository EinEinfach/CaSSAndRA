import logging
logger = logging.getLogger(__name__)
from threading import Thread, Event
from datetime import datetime
import time
import os

from . data import saveddata, calceddata, cleandata, cfgdata, logdata
from .comm.connections import mqttcomm, httpcomm, uartcomm

restart = Event()

#from data import saveddata
#from comm import mqttcomm, cmdlist, cmdtorover, comcfg

def connect_http(restart: Event, file_paths: tuple) -> None:
    start_time_state = datetime.now()
    start_time_obstacles = datetime.now()
    start_time_stats = datetime.now()
    start_time_save = datetime.now()
    time_to_wait = 1
    data_clean_finished = False
    time.sleep(2*time_to_wait)
    while True:
        if restart.is_set():
            logger.info('Server thread is stopped')
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
            
        if (datetime.now() - start_time_save).seconds >= 600*time_to_wait:
            logger.info('Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            start_time_save = datetime.now()
        calceddata.calc_rover_state()
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def connect_mqtt(restart: Event, file_paths: tuple) -> None:
    start_time_save = datetime.now()
    time_to_wait = 1
    data_clean_finished = False

    while True:
        if restart.is_set():
            logger.info('Server thread is stopped')
            mqttcomm.disconnect()
            return
        
        mqttcomm.cmd_to_rover()
        if (datetime.now() - start_time_save).seconds >= 600*time_to_wait:
            logger.info('Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            start_time_save = datetime.now()
        calceddata.calc_rover_state()     
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def connect_uart(restart: Event, file_paths: tuple) -> None:
    start_time_state = datetime.now()
    start_time_obstacles = datetime.now()
    start_time_stats = datetime.now()
    start_time_save = datetime.now()
    time_to_wait = 1
    data_clean_finished = False
    time.sleep(2*time_to_wait)
    while True:
        if restart.is_set():
            if uartcomm.uart_status:
                uartcomm.client.close()
            logger.info('Server thread is stopped')
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
            elif (datetime.now() - start_time_obstacles).seconds > 10*time_to_wait:
                uartcomm.get_stats()
                start_time_obstacles = datetime.now()
            elif (datetime.now() - start_time_stats).seconds > 60*time_to_wait:
                uartcomm.get_stats()
                start_time_stats = datetime.now()
            uartcomm.cmd_to_rover()
            
        if (datetime.now() - start_time_save).seconds >= 600*time_to_wait:
            logger.info('Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            start_time_save = datetime.now()
        calceddata.calc_rover_state()     
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def start(file_paths) -> None:
    logger.info('Backend: Starting backend server')
    logger.debug(f'Backend: Using {file_paths.data} for config and data storage')

    logger.info('Backend: Read communication config file')
    
    # todo: this should be refactored so the class is initialized with correct data immediately
    logdata.commlog.path = file_paths.log
    
    # todo: this should be a class or refactored in some way to avoid having to initilize this way
    #cfg.file_paths = file_paths
    #connect_data = cfg.read_commcfg(file_paths.user.comm)
    
    
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
            logger.info('Starting server thread')
            connection_thread = Thread(target=connect_mqtt, args=(restart, file_paths))
            connection_thread.setDaemon(True)
            connection_thread.start()

            logger.info('Backend is successfully started')
        else:
            logger.info('Backend is running without communication to the rover')
        
    elif connect_data['USE'] == 'HTTP':
        logger.info('Selected connection HTTP')
        httpcomm.create()
        logger.info('Starting server thread')
        connection_thread = Thread(target=connect_http, args=(restart, file_paths))
        connection_thread.setDaemon(True)
        connection_thread.start()
        logger.info('Backend is successfully started')
    
    elif connect_data['USE'] == 'UART':
        logger.info('Selected connection UART')
        uartcomm.create()
        logger.info('Backend: Starting server thread')
        connection_thread = Thread(target=connect_uart, args=(restart, file_paths))
        connection_thread.setDaemon(True)
        connection_thread.start()
        logger.info('Backend is successfully started')

    else:
        logger.error('Backend start is failed')
    
    #give some times to establish connection
    time.sleep(2)

def stop() -> None:
    logger.info('Backend: Save and reboot')
    restart.set()
    time.sleep(5)
    restart.clear()
    start(cfgdata.file_paths)

if __name__ == '__main__':
    start()