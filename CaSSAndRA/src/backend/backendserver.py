import logging
logger = logging.getLogger(__name__)
from threading import Thread, Event
import time
import os

from . data import saveddata, calceddata, cleandata
from . comm import mqttcomm, httpcomm, uartcomm, cfg

restart = Event()

#from data import saveddata
#from comm import mqttcomm, cmdlist, cmdtorover, comcfg

def connect_http(connect_data: dict(), connection: int, restart: Event, absolute_path: str()) -> None:
    #httpcomm.start_http(connect_data, connection_status)
    stats_couter = 0
    state_counter = 0
    save_cnt = 0
    data_clean_finished = False

    while True:
        if restart.is_set():
            logger.info('Backend: Server thread is stopped')
            return
        elif connection[0] != 200:
            connection = httpcomm.connect_http(connect_data)
        else:
            if state_counter == 10:
                connection_status = httpcomm.get_state(connect_data, connection)
                connection[0] = connection_status
                state_counter = 0
            if stats_couter == 150:
                connection_status = httpcomm.get_stats(connect_data, connection)
                connection[0] = connection_status
                stats_couter = 0
            state_counter += 1
            stats_couter += 1
            save_cnt += 1

            connection_status = httpcomm.cmd_to_rover(connect_data, connection)
            connection[0] = connection_status

        if save_cnt >= 1500:
            logger.info('Backend: Writing State-Data to the file')
            saveddata.save('state')
            logger.info('Backend: Writing Statistics-Data to the file')
            saveddata.save('stats')
            # logger.info('Backend: Writing Map-Data to the file')
            # saveddata.save('perimeter', absolute_path)
            save_cnt = 0
        
        calceddata.calc_rover_state()
        data_clean_finished = cleandata.check(data_clean_finished)

        time.sleep(0.4)

def connect_mqtt(mqtt_client, connect_data: dict(), restart: Event, absolute_path: str()) -> None:
    save_cnt = 0
    data_clean_finished = False

    mqttcomm.start_mqtt(mqtt_client, connect_data)
    while True:
        if restart.is_set():
            logger.info('Backend: Server thread is stopped')
            mqtt_client.disconnect()
            return
        
        mqttcomm.cmd_to_rover(mqtt_client, connect_data)
        save_cnt += 1
        if save_cnt >= 6000:
            logger.info('Backend: Writing State-Data to the file')
            saveddata.save('state')
            logger.info('Backend: Writing Statistics-Data to the file')
            saveddata.save('stats')
            # logger.info('Backend: Writing Map-Data to the file')
            # saveddata.save('perimeter', absolute_path)
            save_cnt = 0
             
        calceddata.calc_rover_state()     
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def connect_uart(ser, connect_data: dict(), connection: bool,restart: Event, absolute_path: str()) -> None:
    save_cnt = 0
    data_clean_finished = False
    start_state = time.time()
    start_stats = time.time()
    while True:
        if restart.is_set():
            logger.info('Backend: Server thread is stopped')
            return
        if not connection:
            time.sleep(1)
            ser, connection = uartcomm.connect_uart(connect_data)
        else: 
            if ser.in_waiting > 0:
                try: 
                    data = ser.readline().decode('utf-8').rstrip()
                    logger.debug(data)
                    if data.find('S,') == 0:
                        #logger.debug(data)
                        uartcomm.on_state(data)
                    if data.find('T, ') == 0:
                        #logger.debug(data)
                        uartcomm.on_stats(data)
                    perform_state_req = time.time() - start_state
                    perform_stats_req = time.time() - start_stats  
                    if perform_state_req > 4:
                        start_state = time.time()
                        ser.write(b'AT+S\n')
                    elif perform_stats_req > 60:
                        start_stats = time.time()
                        ser.write(b'AT+T\n')
                except Exception as e:
                    logger.warning('Backend: Exception in UART communication occur, trying to reconnect')
                    logger.debug(str(e))
                    connection = False

            connection = uartcomm.cmd_to_rover(ser)

        save_cnt += 1
        if save_cnt >= 6000:
            logger.info('Backend: Writing State-Data to the file')
            saveddata.save('state')
            logger.info('Backend: Writing Statistics-Data to the file')
            saveddata.save('stats')
            # logger.info('Backend: Writing Map-Data to the file')
            # saveddata.save('perimeter', absolute_path)
            save_cnt = 0

        calceddata.calc_rover_state()     
        data_clean_finished = cleandata.check(data_clean_finished)
        time.sleep(0.1)

def start() -> None:
    absolute_path = os.path.dirname(__file__) 
    logger.debug('absolute_path: '+absolute_path)
    logger.info('Backend: Read communication config file')
    connect_data = cfg.read_commcfg(absolute_path)
    logger.info('Backend: Read map config file')
    cfg.read_mapcfg(absolute_path)
    logger.info('Backend: Read app config file')
    cfg.read_appcfg(absolute_path)
    logger.info('Backend: Read saved data')
    saveddata.read(absolute_path)

    # logger.info('Backend: Starting thread for saving data')
    # save_data_thread = threading.Thread(target=save_data)
    # save_data_thread.setDaemon(True)
    # save_data_thread.start()

    if connect_data['USE'] == 'MQTT':
        logger.info('Backend: Establishing MQTT connection to the MQTT-Server')
        mqtt_client = mqttcomm.connect_mqtt(connect_data)
        mqttcomm.subscribe(mqtt_client, connect_data)
        if mqtt_client.connection_flag:
            logger.info('Backend: Starting server thread')
            connection_thread = Thread(target=connect_mqtt, args=(mqtt_client, connect_data, restart, absolute_path))
            connection_thread.setDaemon(True)
            connection_thread.start()

            logger.info('Backend: Backend is successfully started')
        else:
            logger.info('Backend: Backend server is running without communication to the rover')
        
    elif connect_data['USE'] == 'HTTP':
        logger.info('Backend: Establishing HTTP connection to the rover')
        connection = httpcomm.connect_http(connect_data)
        logger.info('Backend: Starting server thread')
        connection_thread = Thread(target=connect_http, args=(connect_data, connection, restart, absolute_path))
        connection_thread.setDaemon(True)
        connection_thread.start()
        logger.info('Backend: Backend is successfully started')
    
    elif connect_data['USE'] == 'UART':
        logger.info('Backend: Establishing UART communication to the rover')
        ser, connection = uartcomm.connect_uart(connect_data)
        logger.info('Backend: Starting server thread')
        connection_thread = Thread(target=connect_uart, args=(ser, connect_data, connection, restart, absolute_path))
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
    start()

if __name__ == '__main__':
    start()