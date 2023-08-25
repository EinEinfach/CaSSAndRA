import logging
logger = logging.getLogger(__name__)

from datetime import datetime

version = '0.53.4'

commcfg = {
            "USE": "HTTP",
            "MQTT": [
                {
                    "CLIENT_ID": "Ardumower"
                },
                {
                    "USERNAME": ""
                },
                {
                    "PASSWORD": ""
                },
                {
                    "MQTT_SERVER": "192.168.1.1"
                },
                {
                    "PORT": 1883
                },
                {
                    "MOWER_NAME": "Ardumower"
                }
            ],
            "HTTP": [
                {
                    "IP": "http://192.168.1.1"
                },
                {
                    "PASSWORD": "123456"
                }
            ],
            "UART": [
                {
                    "SERPORT": "/dev/ttyACM0"
                },
                {
                    "BAUDRATE": 115200
                }
            ]
        }

datamaxage = int()
time_to_offline = int()
soc_lookup_table = list()
current_thd_charge = float()
time_buttongo_pressed = datetime.now()