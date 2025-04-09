import logging
logger = logging.getLogger(__name__)

# imports
from dataclasses import dataclass, field
from datetime import datetime
import time, threading, os, json, psutil

# local imports
from src.pathdata import paths
from src.backend.data import appdata, cfgdata, saveddata, calceddata, cleandata
from src.backend.data.scheduledata import schedule_tasks
from src.backend.data.mapdata import current_map
from src.backend.data.roverdata import robot
from src.backend.comm.api import cassandra_api
from src.backend.comm.messageservice import messageservice

from src.backend.comm.connections import mqttcomm, httpcomm, uartcomm, mqttapi

@dataclass
class Server:
    sw: str = 'CaSSAndRA'
    version: str = appdata.version
    restart = threading.Event()
    connection_thread = None
    api_thread = None
    api_cmd_thread = None
    message_servive_thread = None
    datastorage_thread = None
    schedule_thread = None
    server_info_thread = None
    cpu_load: float = None
    cpu_temp: float = None
    mem_usage: float = None
    hdd_usage: float = None

    def _runServerInfoLoop(self) -> None:
        while True:
            if self.restart.is_set():
                logger.info('Server info thread is stopped')
                return
            try:
                self.cpu_load = psutil.cpu_percent(interval=2)
                self.mem_usage = psutil.virtual_memory().percent
                self.hdd_usage = psutil.disk_usage('/').percent
                self.cpu_temp = psutil.sensors_temperatures()['cpu_thermal'][0].current
            except:
                self.cpu_temp = None

    def _runScheduleLoop(self) -> None:
        while True:
            if self.restart.is_set():
                logger.info('Schedule thread is stopped')
                return
            schedule_tasks.check()
            time.sleep(60)

    def _runDataStorage(self) -> None:
        start_time_save = datetime.now()
        time_to_wait = 1
        while True:
            if self.restart.is_set():
                logger.info('Data storage thread is stopped')
                logger.info('Writing State-Data to the file')
                saveddata.save('state', paths.file_paths)
                logger.info('Writing Statistics-Data to the file')
                saveddata.save('stats', paths.file_paths)
                return
            if (datetime.now() - start_time_save).seconds >= 1800*time_to_wait:
                logger.info('Writing State-Data to the file')
                saveddata.save('state', paths.file_paths)
                logger.info('Writing Statistics-Data to the file')
                saveddata.save('stats', paths.file_paths)
                start_time_save = datetime.now()
            time.sleep(1)

    def _runMessageService(self) -> None:
        while True:
            if self.restart.is_set():
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

    def _runApi(self) -> None:
        start_time_api = datetime.now()
        time_to_wait = 1
        while True:
            time_start = datetime.now().microsecond
            if cassandra_api.restart_server:
                cassandra_api.restart_server = False
                logger.info('API thread is stopped')
                mqttapi.disconnect()
                self.reboot()
                return
            if cassandra_api.check_auto_shutdown:
                cassandra_api.check_auto_shutdown = False
                self.autoShutdown()
            if cassandra_api.shutdown_server:
                cassandra_api.shutdown_server = False
                self.shutdown()
            if self.restart.is_set():
                logger.info('API thread is stopped')
                mqttapi.disconnect()
                return
            if (datetime.now() - start_time_api).seconds >= 2*time_to_wait:
                logger.debug('Update api data')
                cassandra_api.updatePayload()
                cassandra_api.publish('status', cassandra_api.apistate)
                cassandra_api.publish('server', json.dumps(dict(software=self.sw, version=self.version, cpuLoad=self.cpu_load, cpuTemp=self.cpu_temp, memUsage=self.mem_usage, hddUsage=self.hdd_usage)))
                cassandra_api.publish('robot', cassandra_api.robotstate_json)
                cassandra_api.publish('maps', cassandra_api.mapsstate_json)
                cassandra_api.publish('tasks', cassandra_api.tasksstate_json)
                cassandra_api.publish('mowParameters', cassandra_api.mowparametersstate_json)
                cassandra_api.publish('map', cassandra_api.mapstate_json)
                cassandra_api.publish('schedule', cassandra_api.schedulecfgstate_json)
                start_time_api = datetime.now()
            time.sleep(0.1)

    def _runApiCmd(self) -> None:
        while True:
            if self.restart.is_set():
                logger.info('API cmd thread is stopped')
                return
            if mqttapi.buffer_api != []:
                # cassandra_api.apistate = 'busy'
                # cassandra_api.publish('status', cassandra_api.apistate)
                cassandra_api.checkCmd(mqttapi.buffer_api[0])
                del mqttapi.buffer_api[0]
            time.sleep(0.1)

    def _runMqtt(self) -> None:
        data_clean_finished = False
        while True:
            if self.restart.is_set():
                logger.info('Connection thread is stopped')
                mqttcomm.disconnect()
                return
            
            current_map.update_map()
            mqttcomm.cmd_to_rover()
            calceddata.calc_rover_state()     
            data_clean_finished = cleandata.check(data_clean_finished)
            time.sleep(0.1)
    
    def _runHttp(self) -> None:
        start_time_state = datetime.now()
        start_time_obstacles = datetime.now()
        start_time_stats = datetime.now()
        time_to_wait = 1
        data_clean_finished = False
        time.sleep(2*time_to_wait)
        while True:
            if self.restart.is_set():
                logger.info('Connection thread is stopped')
                return
            elif httpcomm.http_status != 200:
                time.sleep(4)
                httpcomm.connect()
            else:
                if (datetime.now() - start_time_state).seconds > time_to_wait:
                    current_map.update_map()
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
    
    def _runUart(self) -> None:
        start_time_state = datetime.now()
        start_time_obstacles = datetime.now()
        start_time_stats = datetime.now()
        time_to_wait = 1
        data_clean_finished = False
        time.sleep(2*time_to_wait)
        while True:
            if self.restart.is_set():
                uartcomm.client.close()
                logger.info('Connection thread is stopped')
                logger.info('Starting delay time')
                time.sleep(10)
                return
            if not uartcomm.uart_status:
                time.sleep(10)
                uartcomm.connect()
            else: 
                uartcomm.check_buffer()
                if (datetime.now() - start_time_state).seconds > time_to_wait:
                    current_map.update_map()
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

    def setup(self, file_paths) -> None:
        logger.info(f'{self.sw} {self.version}')
        logger.info('Starting server')
        logger.debug(f'Using {file_paths.data} for config and data storage')

        # initialize config data
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
        saveddata.file_paths = paths.file_paths
        logger.info('Read saved data')
        saveddata.read(paths.file_paths.measure)
        logger.info('Read map data file')
        saveddata.read_perimeter(paths.file_paths.map)
        logger.info('Read tasks data file')
        saveddata.read_tasks(paths.file_paths.map)

        #read schedule tasks
        schedule_tasks.load_task_order(cfgdata.schedulecfg)

        #setup robot connection
        self._setupRobotConnection()
        #setup api connection
        self._setupApiConnection()
        #setup message service connection
        self._setupMessageServiceConnection()
        #setup data storage loop
        self._setupDataStorageLoop()
        #setup schedule loop
        self._setupScheduleLoop()
        #setup server info loop
        self._setupServerInfoLoop()
    
    def run(self) -> None:
        logger.info('Starting server info thread')
        self.server_info_thread.start()
        logger.info('Starting robot connection thread')
        self.connection_thread.start()
        logger.info('Starting data storage thread')
        self.datastorage_thread.start()
        logger.info('Starting schedule thread')
        self.schedule_thread.start()
        if cfgdata.commcfg.api == 'MQTT':
            logger.info('Starting api thread')
            self.api_thread.start()
            self.api_cmd_thread.start()
        if cfgdata.commcfg.message_service != None:
            logger.info('Starting message service thread')
            self.message_servive_thread.start()  
        
        #give some times to establish connection
        time.sleep(2)

    def reboot(self) -> None:
        logger.info('Server is being restarted')
        self.restart.set()
        data_storage_running = True
        while data_storage_running:
            data_storage_running = False
            for th in threading.enumerate():
                if th.name == 'data storage':
                    data_storage_running = True
        time.sleep(5)
        self.restart.clear()
        self.setup(paths.file_paths)
        self.run()

    def stop(self) -> None:
        logger.info('Server is being shut down')
        self.restart.set()
        time.sleep(1)
        data_storage_running = True
        while data_storage_running:
            data_storage_running = False
            for th in threading.enumerate():
                if th.name == 'data storage':
                    data_storage_running = True
        self.restart.clear()

    def autoShutdown(self) -> None:
        if cfgdata.commcfg.use == 'UART':
            self.shutdown()
    
    def shutdown(self) -> None:
        logger.info('OS will shutdown.')
        os.system('sudo shutdown -h now')
        
    def _setupRobotConnection(self) -> None:
        if cfgdata.commcfg.use == 'MQTT':
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
            self.connection_thread = threading.Thread(target=self._runMqtt, name='connection')
        elif cfgdata.commcfg.use == 'HTTP':
            logger.info('Selected connection HTTP')
            httpcomm.create()
            self.connection_thread = threading.Thread(target=self._runHttp, name='connection')
        elif cfgdata.commcfg.use == 'UART':
            logger.info('Selected connection UART')
            uartcomm.create()
            self.connection_thread = threading.Thread(target=self._runUart, name='connection')

        self.connection_thread.daemon = True
        
    def _setupApiConnection(self) -> None:
        if cfgdata.commcfg.api == 'MQTT':
            logger.info('Selected API is MQTT')
            topics = {'TOPIC_API_CMD':'api_cmd'}
            cfg = cfg = dict(CLIENT_ID=cfgdata.commcfg.api_mqtt_client_id, USERNAME=cfgdata.commcfg.api_mqtt_username, PASSWORD=cfgdata.commcfg.api_mqtt_pass,
                             MQTT_SERVER=cfgdata.commcfg.api_mqtt_server, PORT=cfgdata.commcfg.api_mqtt_port, NAME=cfgdata.commcfg.api_mqtt_cassandra_server_name)
            mqttapi.create(cfg, topics)
            mqttapi.connect()
            connection_start = datetime.now()
            while mqttapi.client.connection_flag != True:
                time.sleep(0.1)
                if (datetime.now()-connection_start).seconds >10:
                    break
            if mqttapi.client.connection_flag:
                mqttapi.client.publish(mqttapi.mqtt_mower_name+'/status', 'boot')
            self.api_thread = threading.Thread(target=self._runApi, name='api')
            self.api_cmd_thread = threading.Thread(target=self._runApiCmd, name='api cmd')
            self.api_thread.daemon = True
            self.api_cmd_thread.daemon = True
    
    def _setupMessageServiceConnection(self) -> None:
        if cfgdata.commcfg.message_service == 'Telegram':
            messageservice.telegram_token = cfgdata.commcfg.telegram_token
            logger.info('Message service is telegram, check for chat id')
            message_service_connection = messageservice.get_chat_id()
            if message_service_connection == 0:
                self.message_servive_thread = threading.Thread(target=self._runMessageService, name='message service')
                self.message_servive_thread.daemon = True
            else:
                logger.error('Message service could not be started. Check your message service settings.')
                logger.error(f'Error code: {message_service_connection}')
                
        if cfgdata.commcfg.message_service == 'Pushover':
            messageservice.pushover_token = cfgdata.commcfg.pushover_token
            messageservice.pushover_user = cfgdata.commcfg.pushover_user
            self.message_servive_thread = threading.Thread(target=self._runMessageService, name='message service')
            self.message_servive_thread.daemon = True
    
    def _setupDataStorageLoop(self) -> None:
        self.datastorage_thread = threading.Thread(target=self._runDataStorage, name='data storage')
        self.datastorage_thread.daemon = True
    
    def _setupScheduleLoop(self) -> None:
        self.schedule_thread = threading.Thread(target=self._runScheduleLoop, name='schedule_loop')
        self.schedule_thread.daemon = True
    
    def _setupServerInfoLoop(self) -> None:
        self.server_info_thread = threading.Thread(target=self._runServerInfoLoop, name='server_info_loop')
        self.server_info_thread.daemon = True

cassandra = Server()