import logging
logger = logging.getLogger(__name__)
from threading import Thread, Event
from datetime import datetime
import time
import os

from . data import saveddata, calceddata, cleandata, cfgdata, logdata
from . comm import mqttcomm, httpcomm, uartcomm

restart = Event()

#from data import saveddata
#from comm import mqttcomm, cmdlist, cmdtorover, comcfg

def connect_http(connect_data: dict(), connection: int, restart: Event, file_paths: tuple) -> None:
    start_time_state = datetime.now()
    start_time_obstacles = datetime.now()
    start_time_stats = datetime.now()
    start_time_save = datetime.now()
    time_to_wait = 1
    data_clean_finished = False
    time.sleep(2*time_to_wait)
    while True:
        if restart.is_set():
            logger.info('Backend: Server thread is stopped')
            return
        elif connection[0] != 200:
            connection = httpcomm.connect_http(connect_data)
        else:
            if (datetime.now() - start_time_state).seconds > time_to_wait:
                connection_status = httpcomm.get_state(connect_data, connection)
                connection[0] = connection_status
                start_time_state = datetime.now()
            if (datetime.now() - start_time_obstacles).seconds > 10*time_to_wait:
                connection_status = httpcomm.get_obstacles(connect_data, connection)
                connection[0] = connection_status
                start_time_obstacles = datetime.now()
            if (datetime.now() - start_time_stats).seconds > 60*time_to_wait:
                connection_status = httpcomm.get_stats(connect_data, connection)
                connection[0] = connection_status
                start_time_stats = datetime.now()

            connection_status = httpcomm.cmd_to_rover(connect_data, connection)
            connection[0] = connection_status
        if (datetime.now() - start_time_save).seconds >= 600*time_to_wait:
            logger.info('Backend: Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Backend: Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            # logger.info('Backend: Writing Map-Data to the file')
            # saveddata.save('perimeter', absolute_path)
            start_time_save = datetime.now()
        calceddata.calc_rover_state()
        data_clean_finished = cleandata.check(data_clean_finished)

        time.sleep(0.4)

def connect_mqtt(mqtt_client, connect_data: dict(), restart: Event, file_paths: tuple) -> None:
    start_time_save = datetime.now()
    time_to_wait = 1
    data_clean_finished = False

    mqttcomm.start_mqtt(mqtt_client, connect_data)
    while True:
        if restart.is_set():
            logger.info('Backend: Server thread is stopped')
            mqtt_client.disconnect()
            return
        
        mqttcomm.cmd_to_rover(mqtt_client, connect_data)
        if (datetime.now() - start_time_save).seconds >= 600*time_to_wait:
            logger.info('Backend: Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Backend: Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            # logger.info('Backend: Writing Map-Data to the file')
            # saveddata.save('perimeter', absolute_path)
            start_time_save = datetime.now()
             
        calceddata.calc_rover_state()     
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def connect_uart(ser, connect_data: dict(), connection: bool,restart: Event, file_paths: tuple) -> None:
    start_time_state = datetime.now()
    start_time_obstacles = datetime.now()
    start_time_stats = datetime.now()
    start_time_save = datetime.now()
    time_to_wait = 1
    data_clean_finished = False
    time.sleep(2*time_to_wait)
    while True:
        if restart.is_set():
            ser.close()
            logger.info('Backend: Server thread is stopped')
            logger.info('Backend: Starting delay time')
            time.sleep(10)
            return
        if not connection:
            time.sleep(1)
            ser, connection = uartcomm.connect_uart(connect_data)
        else: 
            try: 
                if ser.in_waiting > 0:
                    data = ser.readline().decode('utf-8').rstrip()
                    logger.info('Backend: RX '+data)
                    if data.find('S,') == 0:
                        #logger.debug(data)
                        uartcomm.on_state(data)
                    if data.find('T,') == 0:
                        #logger.debug(data)
                        uartcomm.on_stats(data) 
                    if data.find('S2,') == 0:
                        uartcomm.on_obstacle(data)
                if (datetime.now() - start_time_state).seconds > time_to_wait:
                    ser.write(b'AT+S\n')
                    start_time_state = datetime.now()
                elif (datetime.now() - start_time_obstacles).seconds > 10*time_to_wait:
                    ser.write(b'AT+S2\n')
                    start_time_obstacles = datetime.now()
                elif (datetime.now() - start_time_stats).seconds > 60*time_to_wait:
                    ser.write(b'AT+T\n')
                    start_time_stats = datetime.now()
                connection = uartcomm.cmd_to_rover(ser)
            except Exception as e:
                logger.warning('Backend: Exception in UART communication occured, trying to reconnect')
                logger.debug(str(e))
                ser.close()
                connection = False

        if (datetime.now() - start_time_save).seconds >= 600*time_to_wait:
            logger.info('Backend: Writing State-Data to the file')
            saveddata.save('state', file_paths)
            logger.info('Backend: Writing Statistics-Data to the file')
            saveddata.save('stats', file_paths)
            # logger.info('Backend: Writing Map-Data to the file')
            # saveddata.save('perimeter', absolute_path)
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
        logger.info('Backend: Establishing MQTT connection to the MQTT-Server')
        mqtt_client = mqttcomm.connect_mqtt(connect_data)
        
        if mqtt_client.connection_flag:
            logger.info('Backend: Starting server thread')
            connection_thread = Thread(target=connect_mqtt, args=(mqtt_client, connect_data, restart, file_paths))
            connection_thread.setDaemon(True)
            connection_thread.start()

            logger.info('Backend: Backend is successfully started')
        else:
            logger.info('Backend: Backend server is running without communication to the rover')
        
    elif connect_data['USE'] == 'HTTP':
        logger.info('Backend: Establishing HTTP connection to the rover')
        connection = httpcomm.connect_http(connect_data)
        logger.info('Backend: Starting server thread')
        connection_thread = Thread(target=connect_http, args=(connect_data, connection, restart, file_paths))
        connection_thread.setDaemon(True)
        connection_thread.start()
        logger.info('Backend: Backend is successfully started')
    
    elif connect_data['USE'] == 'UART':
        logger.info('Backend: Establishing UART communication to the rover')
        ser, connection = uartcomm.connect_uart(connect_data)
        logger.info('Backend: Starting server thread')
        connection_thread = Thread(target=connect_uart, args=(ser, connect_data, connection, restart, file_paths))
        connection_thread.setDaemon(True)
        connection_thread.start()
        logger.info('Backend: Backend is successfully started')

    else:
        logger.error('Backend: Backend start is failed')
    
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