import logging
logger = logging.getLogger(__name__)

#package imports
import os
import json
from dataclasses import dataclass, field
import base64
import pandas as pd
from PIL import Image

file_paths = None

#commcfg class
@dataclass
class CommCfg:
    use: str = 'HTTP'
    mqtt_client_id: str = 'CaSSAndRA'
    mqtt_username: str = ''
    mqtt_pass: str = ''
    mqtt_server: str = '192.168.1.1'
    mqtt_port: int = 1883
    mqtt_mower_name: str = 'Ardumower'
    http_ip: str = '192.168.1.1'
    http_pass: int = 123456
    uart_port: str = '/dev/ttyACM0'
    uart_baudrate: int = 115200
    api: str = None
    api_mqtt_client_id: str = 'CaSSAndRA_api'
    api_mqtt_username: str = ''
    api_mqtt_pass: str = ''
    api_mqtt_server: str = '192.168.1.1'
    api_mqtt_port: int = 1883
    api_mqtt_cassandra_server_name:str = 'myCaSSAndRA'
    message_service: str = None
    telegram_token: str = None
    telegram_chat_id: int = None
    pushover_token: str = None
    pushover_user: str = None
    
    def read_commcfg(self) -> dict:
        try:
            with open(file_paths.user.comm) as f: 
                commcfg_from_file = json.load(f)
                f.close()
                logger.debug('Backend: commcfg to read: '+ str(commcfg_from_file))
                self.use = commcfg_from_file['USE']
                self.mqtt_client_id = commcfg_from_file['MQTT'][0]['CLIENT_ID']
                self.mqtt_username = commcfg_from_file['MQTT'][1]['USERNAME']
                self.mqtt_pass = commcfg_from_file['MQTT'][2]['PASSWORD']
                self.mqtt_server = commcfg_from_file['MQTT'][3]['MQTT_SERVER']
                self.mqtt_port = commcfg_from_file['MQTT'][4]['PORT'] 
                self.mqtt_mower_name = commcfg_from_file['MQTT'][5]['MOWER_NAME']
                self.http_ip = commcfg_from_file['HTTP'][0]['IP']
                self.http_pass = commcfg_from_file['HTTP'][1]['PASSWORD']
                self.uart_port = commcfg_from_file['UART'][0]['SERPORT']
                self.uart_baudrate = commcfg_from_file['UART'][1]['BAUDRATE']
                self.api = commcfg_from_file['API']
                self.api_mqtt_client_id = commcfg_from_file['MQTT_API'][0]['CLIENT_ID']
                self.api_mqtt_username = commcfg_from_file['MQTT_API'][1]['USERNAME']
                self.api_mqtt_pass = commcfg_from_file['MQTT_API'][2]['PASSWORD']
                self.api_mqtt_server = commcfg_from_file['MQTT_API'][3]['MQTT_SERVER']
                self.api_mqtt_port = commcfg_from_file['MQTT_API'][4]['PORT'] 
                self.api_mqtt_cassandra_server_name = commcfg_from_file['MQTT_API'][5]['API_SERVER_NAME']
                self.message_service = commcfg_from_file['MESSAGE_SERVICE']
                self.telegram_token = commcfg_from_file['TELEGRAM'][0]['TOKEN']
                self.telegram_chat_id = commcfg_from_file['TELEGRAM'][1]['CHAT_ID']
                self.pushover_token = commcfg_from_file['PUSHOVER'][0]['TOKEN']
                self.pushover_user = commcfg_from_file['PUSHOVER'][1]['USER']
                return commcfg_from_file
        except Exception as e:
            logger.error('Could not read commcfg.json. Missing commcfg.json. Go with standard values')
            logger.debug(str(e))
            res = self.save_commcfg()
            with open (file_paths.user.comm) as f: 
                commcfg_from_file = json.load(f)
                f.close()
                return commcfg_from_file
        
    def save_commcfg(self) -> None:
        try:
            new_data = dict()
            new_data['USE'] = self.use
            new_data['MQTT'] = [{'CLIENT_ID': self.mqtt_client_id}, 
                                {'USERNAME': self.mqtt_username},
                                {'PASSWORD': self.mqtt_pass},
                                {'MQTT_SERVER': self.mqtt_server},
                                {'PORT': self.mqtt_port},
                                {'MOWER_NAME': self.mqtt_mower_name}
                                ]
            new_data['HTTP'] = [{'IP': self.http_ip},
                                {'PASSWORD': self.http_pass},
                                ]
            new_data['UART'] = [{'SERPORT': self.uart_port},
                                {'BAUDRATE': self.uart_baudrate}
                                ]
            new_data['API'] = self.api
            new_data['MQTT_API'] = [{'CLIENT_ID': self.api_mqtt_client_id}, 
                                {'USERNAME': self.api_mqtt_username},
                                {'PASSWORD': self.api_mqtt_pass},
                                {'MQTT_SERVER': self.api_mqtt_server},
                                {'PORT': self.api_mqtt_port},
                                {'API_SERVER_NAME': self.api_mqtt_cassandra_server_name}
                                ]
            new_data['MESSAGE_SERVICE'] = self.message_service
            new_data['TELEGRAM'] = [{'TOKEN': self.telegram_token},
                                    {'CHAT_ID': self.telegram_chat_id}]
            new_data['PUSHOVER'] = [{'TOKEN': self.pushover_token},
                                    {'USER': self.pushover_user}]
            with open(file_paths.user.comm, 'w') as f:
                logger.debug('New commcfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('commcfg data are successfully stored in commcfg.json')
            return 0
        except Exception as e:
            logger.error('Could not save commcfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1

#appcfg class
@dataclass
class AppCfg:
    datamaxage: int = 30
    time_to_offline: int = 60
    voltage_0: float = 22
    voltage_100: float = 28
    current_thd_charge: float = -0.03
    rover_picture: str = 'default/'
    rover_pictures: Image = None
    obstacles_amount: int = 0
    file_path: str = ''
    light_mode: bool = True

    def read_appcfg(self) -> None:
        try:
            with open(file_paths.user.appcfg) as f: 
                appcfg_from_file = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Could not read appcfg.json. Missing appcfg.json. Go with standard values')
            logger.debug(str(e))
            res = self.save_appcfg()
            return
        try:
            logger.debug('appcfg to read: '+ str(appcfg_from_file))
            self.datamaxage = appcfg_from_file['datamaxage']
            self.time_to_offline = appcfg_from_file['time_to_offline']
            self.voltage_0 = appcfg_from_file['voltage_to_soc'][0]['V']
            self.voltage_100 = appcfg_from_file['voltage_to_soc'][1]['V']
            self.current_thd_charge = appcfg_from_file['current_thd_charge']
            self.rover_picture = appcfg_from_file['rover_picture']
            self.rover_pictures = Image.open(os.path.dirname(__file__).replace('/backend/data', '/assets/icons/'+self.rover_picture)+'rover0grad.png')
            self.obstacles_amount = appcfg_from_file['obstacles_amount']
            self.light_mode = appcfg_from_file['light_mode']
        except Exception as e:
            logger.error('Could not read appcfg.json. Data are invalid. Go with standard values')
            logger.debug(str(e))
            res = self.save_appcfg()
    
    def save_appcfg(self) -> int:
        try:
            new_data = dict()
            new_data['datamaxage'] = self.datamaxage
            new_data['time_to_offline'] = self.time_to_offline
            soc_look_up_table = [{'V': self.voltage_0, 'SoC': 0}, {'V': self.voltage_100, 'SoC': 100}]
            new_data['voltage_to_soc'] = soc_look_up_table
            new_data['current_thd_charge'] = self.current_thd_charge
            new_data['rover_picture'] = self.rover_picture
            new_data['obstacles_amount'] = self.obstacles_amount
            new_data['light_mode'] = self.light_mode
            with open(file_paths.user.appcfg, 'w') as f:
                logger.debug('New appcfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('appcfg data are successfully stored in appcfg.json')
            return 0
        except Exception as e:
            logger.error('Could not save appcfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1
    
    def show_preview_image(self, path: str) -> str:
        encoded_image = base64.b64encode(open(os.path.dirname(__file__).replace('/backend/data', '/assets/icons/'+path+'rover90grad.png'), 'rb').read())
        return 'data:image/png;base64,{}'.format(encoded_image.decode()) 

#rovercfg class
@dataclass
class RoverCfg:
    mowspeed_setpoint: float = 0.3
    gotospeed_setpoint: float = 0.5
    positionmode: str = 'relative'
    lon: float = 0
    lat: float = 0
    fix_timeout = 60

    def read_rovercfg(self) -> None:
        try:
            with open(file_paths.user.rovercfg) as f: 
                rovercfg_from_file = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Could not read rovercfg.json. Missing rovercfg.json. Go with standard values')
            logger.debug(str(e))
            res = self.save_rovercfg()
            return
        try:
            logger.debug('rovercfg to read: '+ str(rovercfg_from_file))
            self.mowspeed_setpoint = rovercfg_from_file['mowspeed_setpoint']
            self.gotospeed_setpoint = rovercfg_from_file['gotospeed_setpoint']
            self.positionmode = rovercfg_from_file['positionmode']
            self.lon = rovercfg_from_file['lon']
            self.lat = rovercfg_from_file['lat']
            self.fix_timeout = rovercfg_from_file['fix_timeout']
        except Exception as e:
            logger.error('Could not read rovercfg.json. Data are invalid. Go with standard values')
            res = self.save_rovercfg()
    
    def save_rovercfg(self) -> int:
        try:
            new_data = dict()
            new_data['mowspeed_setpoint'] = self.mowspeed_setpoint
            new_data['gotospeed_setpoint'] = self.gotospeed_setpoint
            new_data['positionmode'] = self.positionmode
            new_data['lon'] = self.lon
            new_data['lat'] = self.lat
            new_data['fix_timeout'] = self.fix_timeout
            with open(file_paths.user.rovercfg, 'w') as f:
                logger.debug('New rovercfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('rovercfg data are successfully stored in rovercfg.json')
            return 0
        except Exception as e:
            logger.error('Could not save rovercfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1

#coverage path planner config class
@dataclass
class PathPlannerCfg:
    pattern: str = 'lines'
    width: float = 0.18
    angle: int = 0
    distancetoborder: int = 1
    mowarea: bool = True
    mowborder: int = 1
    mowexclusion: bool = True
    mowborderccw: bool = True

    def read_pathplannercfg(self) -> None:
        try:
            with open(file_paths.user.pathplannercfg) as f: 
                pathplannercfg_from_file = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Could not read pathplannercfg.json. Missing pathplannercfg.json. Go with standard values')
            logger.debug(str(e))
            res = self.save_pathplannercfg()
            return
        try:
            logger.debug('pahtplannercfg to read: '+ str(pathplannercfg_from_file))
            self.pattern = pathplannercfg_from_file['pattern']
            self.width = pathplannercfg_from_file['width']
            self.angle = pathplannercfg_from_file['angle']
            self.distancetoborder = pathplannercfg_from_file['distancetoborder']
            self.mowarea = pathplannercfg_from_file['mowarea']
            self.mowborder = pathplannercfg_from_file['mowborder']
            self.mowexclusion = pathplannercfg_from_file['mowexclusion']
            self.mowborderccw = pathplannercfg_from_file['mowborderccw']
        except Exception as e:
            logger.error('Could not read pathplannercfg.json. Data are invalid. Go with standard values')
            res = self.save_pathplannercfg()
    
    def save_pathplannercfg(self) -> int:
        try:
            new_data = dict()
            new_data['pattern'] = self.pattern
            new_data['width'] = self.width
            new_data['angle'] = self.angle
            new_data['distancetoborder'] = self.distancetoborder
            new_data['mowarea'] = self.mowarea
            new_data['mowborder'] = self.mowborder
            new_data['mowexclusion'] = self.mowexclusion
            new_data['mowborderccw'] = self.mowborderccw
            with open(file_paths.user.pathplannercfg, 'w') as f:
                logger.debug('New pathplannercfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('pathplannercfg data are successfully stored in pathplannercfg.json')
            return 0
        except Exception as e:
            logger.error('Could not save pathplannercfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1

    def df_to_obj(self, parameters: pd.DataFrame) -> None:
        self.pattern = parameters.iloc[0]['pattern']
        self.width = parameters.iloc[0]['width']
        self.angle = parameters.iloc[0]['angle']
        self.distancetoborder = parameters.iloc[0]['distancetoborder']
        self.mowarea = parameters.iloc[0]['mowarea']
        self.mowborder = parameters.iloc[0]['mowborder']
        self.mowexclusion = parameters.iloc[0]['mowexclusion']
        self.mowborderccw = parameters.iloc[0]['mowborderccw']

@dataclass
class ScheduleCfg:
    active: bool = False
    monday_time: list = field(default_factory=lambda: [12, 12])
    tuesday_time: list = field(default_factory=lambda: [12, 12])
    wednesday_time: list = field(default_factory=lambda: [12, 12])
    thursday_time: list = field(default_factory=lambda: [12, 12])
    friday_time: list = field(default_factory=lambda: [12, 12])
    saturday_time: list = field(default_factory=lambda: [12, 12])
    sunday_time: list = field(default_factory=lambda: [12, 12])
    monday_tasks: list = field(default_factory=list)
    tuesday_tasks: list = field(default_factory=list)
    wednesday_tasks: list = field(default_factory=list)
    thursday_tasks: list = field(default_factory=list)
    friday_tasks: list = field(default_factory=list)
    saturday_tasks: list = field(default_factory=list)
    sunday_tasks: list = field(default_factory=list)

    def reset_schedulecfg(self) -> None:
        self.active = False
        self.monday_time = [12, 12]
        self.tuesday_time = [12, 12]
        self.wednesday_time = [12, 12]
        self.thursday_time = [12, 12]
        self.friday_time = [12, 12]
        self.saturday_time = [12, 12]
        self.sunday_time = [12, 12]
        self.monday_tasks = []
        self.tuesday_tasks = []
        self.wednesday_tasks = []
        self.thursday_tasks = []
        self.friday_tasks = []
        self.saturday_tasks = []
        self.sunday_tasks = []
        self.save_schedulecfg()

    def read_schedulecfg(self) -> None:
        try:
            with open(file_paths.user.schedulecfg) as f: 
                schedulecfg_from_file = json.load(f)
                f.close()
        except Exception as e:
            logger.error('Could not read schedulecfg.json. Missing schedulecfg.json. Go with standard values')
            logger.debug(str(e))
            #res = self.save_schedulecfg()
            return
        try:
            logger.debug('Backend: schedulecfg to read: '+ str(schedulecfg_from_file))
            self.active = schedulecfg_from_file['use_schedule']
            self.monday_time = schedulecfg_from_file['time_range'][0]['monday']
            self.tuesday_time = schedulecfg_from_file['time_range'][1]['tuesday']
            self.wednesday_time = schedulecfg_from_file['time_range'][2]['wednesday']
            self.thursday_time = schedulecfg_from_file['time_range'][3]['thursday']
            self.friday_time = schedulecfg_from_file['time_range'][4]['friday']
            self.saturday_time= schedulecfg_from_file['time_range'][5]['saturday']
            self.sunday_time= schedulecfg_from_file['time_range'][6]['sunday']
            self.monday_tasks = schedulecfg_from_file['tasks'][0]['monday']
            self.tuesday_tasks = schedulecfg_from_file['tasks'][1]['tuesday']
            self.wednesday_tasks = schedulecfg_from_file['tasks'][2]['wednesday']
            self.thursday_tasks = schedulecfg_from_file['tasks'][3]['thursday']
            self.friday_tasks = schedulecfg_from_file['tasks'][4]['friday']
            self.saturday_tasks = schedulecfg_from_file['tasks'][5]['saturday']
            self.sunday_tasks = schedulecfg_from_file['tasks'][6]['sunday']
        except Exception as e:
            logger.error('Could not read schedulecfg.json. Data are invalid. Go with standard values')
            #res = self.save_schedulecfg()
    
    def save_schedulecfg(self) -> int:
        try:
            new_data = dict()
            new_data['use_schedule'] = self.active
            new_data['time_range'] = [{'monday': self.monday_time},
                                      {'tuesday': self.tuesday_time},
                                      {'wednesday': self.wednesday_time},
                                      {'thursday': self.thursday_time},
                                      {'friday': self.friday_time},
                                      {'saturday': self.saturday_time},
                                      {'sunday': self.sunday_time}
                                    ]
            new_data['tasks'] = [{'monday': self.monday_tasks},
                                 {'tuesday': self.tuesday_tasks},
                                 {'wednesday': self.wednesday_tasks},
                                 {'thursday': self.thursday_tasks},
                                 {'friday': self.friday_tasks},
                                 {'saturday': self.saturday_tasks},
                                 {'sunday': self.sunday_tasks}
                                ]
            with open(file_paths.user.schedulecfg, 'w') as f:
                logger.debug('New schedulecfg data: '+str(new_data))
                json.dump(new_data, f, indent=4)
            logger.info('Schedulecfg data are successfully stored in schedulecfg.json')
            return 0
        except Exception as e:
            logger.error('Could not save schedulecfg.json. Unexpected behaivor')
            logger.debug(str(e))
            return -1


commcfg = CommCfg()
rovercfg = RoverCfg()
pathplannercfg = PathPlannerCfg()
pathplannercfgstate = PathPlannerCfg()
pathplannercfgtask = PathPlannerCfg()
pathplannercfgtasktmp = PathPlannerCfg()
pathplannercfgapi = PathPlannerCfg()
appcfg = AppCfg()
schedulecfg = ScheduleCfg()


        