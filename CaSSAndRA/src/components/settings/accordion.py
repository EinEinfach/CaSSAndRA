from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import dash_daq as daq
import time

from .. import ids
from . import buttons
from src.backend import backendserver
from src.backend.data import appdata
from src.backend.data.cfgdata import rovercfg, pathplannercfg, appcfg, commcfg
from src.backend.comm import cmdlist
from src.backend.comm.messageservice import messageservice

accordion_settings = dbc.Accordion([
                        dbc.AccordionItem(
                            [
                                html.P('Which way should use CaSSAndRA for rover connection'),
                                html.Div([
                                    dbc.RadioItems(
                                        options=[
                                            {'label': 'MQTT', 'value': 'MQTT'},
                                            {'label': 'HTTP', 'value': 'HTTP'},
                                            {'label': 'UART', 'value': 'UART'}
                                        ],
                                        id=ids.RADIOCONNECTIONTYPE,
                                        inline=True
                                    ), 
                                ]),
                                html.Div([
                                    html.Div(buttons.savebutton),

                                    html.Div([
                                        dbc.FormText('Client-ID'),
                                        dbc.Input(value = commcfg.mqtt_client_id, id=ids.MQTTCLIENTID),
                                        dbc.FormText('Username'),
                                        dbc.Input(placeholder='your MQTT-Server username, leave empty if not in use', id=ids.MQTTUSERNAME),
                                        dbc.FormText('Password'),
                                        dbc.Input(placeholder='your MQTT-Server password, leave empty if not in use', id=ids.MQTTPASSWORD),
                                        dbc.FormText('MQTT-Server'),
                                        dbc.Input(value = commcfg.mqtt_server, id=ids.MQTTSERVER),
                                        dbc.FormText('Port'),
                                        dbc.Input(value = commcfg.mqtt_port, id=ids.MQTTPORT, type='number'),
                                        dbc.FormText('Mower name with prefix'),
                                        dbc.Input(value = commcfg.mqtt_mower_name, id=ids.MQTTROVERNAME)  
                                    ], id=ids.MQTTCONNECTIONSTYLE),

                                    html.Div([dbc.FormText('IP-Adress of your rover'),
                                        dbc.Input(value = commcfg.http_ip, id=ids.IPADRESSROVER),
                                        dbc.FormText('Connection password (see your config.h)'),
                                        dbc.Input(placeholder='see config.h of sunray FW', id=ids.SUNRAYPASS),
                                    ], id=ids.HTTPCONNECTIONSTYLE),

                                    html.Div([dbc.FormText('Serial port'),
                                        dbc.Input(value = commcfg.uart_port, id=ids.SERPORT),
                                        dbc.FormText('Baudrate'),
                                        dbc.Input(value = commcfg.uart_baudrate, id=ids.BAUDRATE, type='number'),
                                    ], id=ids.UARTCONNECTIONSTYLE)     
                                ]),
                            ],
                            title='Connection',
                        ),
                        dbc.AccordionItem(
                            [
                                html.P('Default settings for task calculation'),
                                html.Div(buttons.savebuttonmapsettings),
                                dbc.FormText('Pattern'),
                                dbc.Select(
                                    id=ids.PATTERNSETTINGS, 
                                    options=[
                                        {'label': 'lines', 'value': 'lines'},
                                        {'label': 'squares', 'value': 'squares'},
                                        {'label': 'rings', 'value': 'rings'},
                                    ],
                                    value=pathplannercfg.pattern
                                ),
                                dbc.FormText('Mow width'),
                                dbc.Input(value=pathplannercfg.width, id=ids.MOWOFFSETSETTINGS, type='number', min=0.01, max=1, step=0.01),
                                dbc.FormText('Mow angle'),
                                dbc.Input(value=pathplannercfg.angle, id=ids.MOWANGLESETTINGS, type='number', min=0, max=359, step=1),
                                dbc.FormText('Distance to border'),
                                dbc.Input(value=pathplannercfg.distancetoborder, id=ids.DISTANCETOBORDERSETTINGS, type='number', min=0, max=5, step=1),
                                dbc.FormText('Mow cut edge border (laps)'),
                                dbc.Input(value=pathplannercfg.mowborder, id=ids.MOWEDGESETTINGS, type='number', min=0, max=6, step=1),
                                dbc.Row(
                                [
                                    dbc.FormText('Mow area'),
                                    html.Div(
                                        dbc.Switch(
                                            id=ids.MOWAREASETTINGS,
                                            value=pathplannercfg.mowarea,
                                            style={"float" : "left"},
                                        ),
                                    ),
                                ]),
                                dbc.Row(
                                [
                                    dbc.FormText('Mow cut edge exclusion'),
                                    html.Div(
                                        dbc.Switch(
                                            id=ids.MOWEDGEEXCLUSIONSETTINGS,
                                            value=pathplannercfg.mowexclusion,
                                            style={"float" : "left"},
                                        ),
                                    ),
                                ]),
                                dbc.Row(
                                [
                                    dbc.FormText('Mow cut edge border in ccw'),
                                    html.Div(
                                        dbc.Switch(
                                            id=ids.MOWBORDERCCWSETTINGS,
                                            value=pathplannercfg.mowborderccw,
                                            style={"float" : "left"},
                                        ),
                                    ),
                                ]),
                            ],
                            title='Coverage path planner',
                        ),
                        dbc.AccordionItem(
                            [
                            html.P('Settings for calculation inside the app'),
                            dbc.Row([
                                dbc.Col([
                                    html.Div(buttons.savebuttonappsettings),
                                ]),
                                dbc.Col([
                                    html.Img(id=ids.ROVERPICTUREPREVIEWSETTINGS, height=80, width=80)
                                ])
                            ]),
                            dbc.FormText('Mower picture'),
                                dbc.Select(
                                    id=ids.ROVERPICTURESETTINGS,
                                    options=[
                                        {'label': 'default', 'value': 'default/'},
                                        {'label': 'ardumower', 'value': 'ardumower/'},
                                        {'label': 'alfred', 'value': 'alfred/'},
                                        {'label': 'landrumower', 'value': 'landrumower/'},
                                    ],
                                    value=appcfg.rover_picture
                                ),
                            dbc.FormText('Max age for measured data [days]'),
                            dbc.Input(value=appcfg.datamaxage, type='number', min=1, step=1, id=ids.MAXAGESETTINGS),
                            dbc.FormText('Time to wait before offline [s]'),
                            dbc.Input(value=appcfg.time_to_offline, type='number', min=30, step=1, id=ids.TIMETOOFFLINESETTINGS),
                            dbc.FormText('Min charge current [A]'),
                            dbc.Input(value=appcfg.current_thd_charge, type='number', max=0, step=0.01, id=ids.CURRENTTHDCHARGESETTINGS),
                            dbc.FormText('Voltage [V] to SoC [%]'),
                            dbc.Row([
                                dbc.Col([
                                    dbc.FormText('Voltage min (0% SoC)'),
                                    dbc.Input(value=appcfg.voltage_0, type='number', min=0, step=0.1, id=ids.VOLTAGEMINSETTINGS),
                                ]),   
                                dbc.Col([
                                    dbc.FormText('Voltage max (100% SoC)'),
                                    dbc.Input(value=appcfg.voltage_100, type='number', min=0, step=0.1, id=ids.VOLTAGEMAXSETTINGS),
                                ]),                         
                            ]),
                            dbc.FormText('Max amount of showing obstacles (0 means synchronous to sunray fw)'),
                            dbc.Input(value=appcfg.obstacles_amount, type='number', min=0, step=1, id=ids.MAXAMOUNTOBSTACLESSETTINGS),
							dbc.FormText('Light mode'),
							dbc.Select(
								id=ids.LIGHTMODESETTINGS,
								options=[
									{'label': 'light', 'value': "True"},
									{'label': 'dark', 'value': "False"},
								],
								value=appcfg.rover_picture
							),
                        ], title='App'),
                        dbc.AccordionItem(
                            [
                            html.P('Default robot settings'),
                            html.Div(buttons.savebuttonrobotsettings),
                            dbc.FormText('Position mode'),
                                html.Div([
                                    dbc.RadioItems(
                                        options=[
                                            {'label': 'absolute', 'value': 'absolute'},
                                            {'label': 'relative', 'value': 'relative'},
                                        ],
                                        value=rovercfg.positionmode,
                                        id=ids.RADIOPOSITIONMODE,
                                        inline=True
                                    ), 
                                ]),
                                html.Div([
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.FormText('Lon'),
                                            dbc.Input(value=rovercfg.lon, id=ids.POSITIONMODELON, type='number'),
                                        ]),
                                        dbc.Col([
                                            dbc.FormText('Lat'),
                                            dbc.Input(value=rovercfg.lat, id=ids.POSITIONMODELAT, type='number'),
                                        ]),
                                    ]),
                                ], id=ids.POSITIONMODESTYLE),
                            dbc.FormText('Default mow speed setpoint [m/s]'),
                            dbc.Input(value=rovercfg.mowspeed_setpoint, type='number', min=0.1, max=1.0, step=0.01, id=ids.MOWSPEEDSETPOINTSETTINGS),
                            dbc.FormText('Default transit speed setpoint [m/s]'),
                            dbc.Input(value=rovercfg.gotospeed_setpoint, type='number', min=0.1, max=1.0, step=0.01, id=ids.GOTOSPEEDSETPOINTSETTINSGS),
                            dbc.FormText('Fix timeout [s]'),
                            dbc.Input(value=rovercfg.fix_timeout, type='number', min=1, step=1, id=ids.FIXTIMEOUTSETTINGS),
                        ], title='Robot'),
                        dbc.AccordionItem(
                            [
                                html.P('Which way should be used for API connection'),
                                html.Div([
                                    dbc.RadioItems(
                                        options=[
                                            {'label': 'deactivated', 'value': 'deactivated'},
                                            {'label': 'MQTT', 'value': 'MQTT'},
                                        ],
                                        id=ids.RADIOAPICONNECTIONTYPE,
                                        inline=True
                                    ), 
                                ]),
                                html.Div([
                                    html.Div(buttons.savebutton),

                                    html.Div(id=ids.APINONECONNECTIONSTYLE),  
                                    html.Div([
                                        dbc.FormText('Client-ID'),
                                        dbc.Input(value = commcfg.api_mqtt_client_id, id=ids.APIMQTTCLIENTID),
                                        dbc.FormText('Username'),
                                        dbc.Input(placeholder='your MQTT-Server username, leave empty if not in use', id=ids.APIMQTTUSERNAME),
                                        dbc.FormText('Password'),
                                        dbc.Input(placeholder='your MQTT-Server password, leave empty if not in use', id=ids.APIMQTTPASSWORD),
                                        dbc.FormText('MQTT-Server'),
                                        dbc.Input(value = commcfg.api_mqtt_server, id=ids.APIMQTTSERVER),
                                        dbc.FormText('Port'),
                                        dbc.Input(value = commcfg.api_mqtt_port, id=ids.APIMQTTPORT, type='number'),
                                        dbc.FormText('Cassandra server name with prefix'),
                                        dbc.Input(value = commcfg.api_mqtt_cassandra_server_name, id=ids.APIMQTTCASSANDRASERVERNAME)  
                                    ], id=ids.APIMQTTCONNECTIONSTYLE), 
                                ]),
                            ],
                            title='API',
                        ),
                        dbc.AccordionItem(
                            [
                                html.P('Should CaSSAndRA send messages to you'),
                                html.Div([
                                    dbc.RadioItems(
                                        options=[
                                            {'label': 'deactivated', 'value': 'deactivated'},
                                            {'label': 'Telegram', 'value': 'Telegram'},
                                            {'label': 'Pushover', 'value': 'Pushover'}
                                        ],
                                        id=ids.RADIOMESSAGESERVICETYPE,
                                        inline=True
                                    ), 
                                ]),
                                html.Div([
                                    html.Div(buttons.savebutton),

                                    html.Div(id=ids.MESSAGESERVICESTYLE),  
                                    dbc.Container([
                                        dbc.FormText('API-Token'),
                                        dbc.Input(id=ids.TELEGRAMTOKEN), 
                                        dbc.FormText('Chat ID'),
                                        dbc.Input(id=ids.TELEGRAMCHATID), 
                                        dbc.FormText('Test message'),
                                        dbc.Row([
                                            dbc.Col([dbc.Input(id=ids.TELEGRAMTESTMESSAGE)], style={"flex" : "1 0 0%"}),
                                            dbc.Col([dbc.Button(id=ids.BUTTONSENDTELEGRAMMESSAGE, 
                                                                size='lg', 
                                                                class_name='bi bi-send-fill', 
                                                                title='send test message'),
                                                    ], style={"flex" : "0 0 0%"}
                                            )
                                            ], justify='center', align='center',
                                        )
                                    ], 
                                    id=ids.TELEGRAMSERVICESTYLE, 
                                    style={"height" : "100%", "overflow" : "hidden", "display" : "flex", "flex-direction" : "column"}), 
                                    dbc.Container([
                                        dbc.FormText('API-Token'),
                                        dbc.Input(id=ids.PUSHOVERTOKEN), 
                                        dbc.FormText('User'),
                                        dbc.Input(id=ids.PUSHOVERUSER), 
                                        dbc.FormText('Test message'),
                                        dbc.Row([
                                            dbc.Col([dbc.Input(id=ids.TELEGRAMTESTMESSAGE)], style={"flex" : "1 0 0%"}),
                                            dbc.Col([dbc.Button(id=ids.BUTTONSENDTELEGRAMMESSAGE, 
                                                                size='lg', 
                                                                class_name='bi bi-send-fill', 
                                                                title='send test message'),
                                                    ], style={"flex" : "0 0 0%"}
                                            )
                                            ], justify='center', align='center',
                                        )
                                    ], 
                                    id=ids.PUSHOVERSERVICESTYLE, 
                                    style={"height" : "100%", "overflow" : "hidden", "display" : "flex", "flex-direction" : "column"}),
                                ]),
                                
                            ],
                            title='Message service',
                        ),
                    ], start_collapsed=True, id=ids.ACCORDIONSETTINGS
                )

@callback(Output(ids.MQTTCONNECTIONSTYLE, 'style'),
          Output(ids.HTTPCONNECTIONSTYLE, 'style'),
          Output(ids.UARTCONNECTIONSTYLE, 'style'),
          Input(ids.RADIOCONNECTIONTYPE, 'value'))
def update_connectioninput(radio_input: str) -> list:
    if radio_input == 'MQTT':
        return {'display': 'block'}, {'display': 'none'}, {'display': 'none'}
    elif radio_input == 'HTTP':
        return {'display': 'none'}, {'display': 'block'}, {'display': 'none'}
    elif radio_input == 'UART':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'block'}
    else:
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
    
@callback(Output(ids.MODALCONNECTION, 'is_open'),
          [Input(ids.BUTTONSAVEANDREBOOT, 'n_clicks'),
           Input(ids.BUTTONOK, 'n_clicks'),
           State(ids.MODALCONNECTION, 'is_open'),
           State(ids.RADIOCONNECTIONTYPE, 'value'),
           State(ids.MQTTCLIENTID, 'value'),
           State(ids.MQTTUSERNAME, 'value'),
           State(ids.MQTTPASSWORD, 'value'),
           State(ids.MQTTSERVER, 'value'),
           State(ids.MQTTPORT, 'value'),
           State(ids.MQTTROVERNAME, 'value'),
           State(ids.IPADRESSROVER, 'value'),
           State(ids.SUNRAYPASS, 'value'),
           State(ids.SERPORT, 'value'),
           State(ids.BAUDRATE, 'value'),
           State(ids.RADIOAPICONNECTIONTYPE, 'value'),
           State(ids.APIMQTTCLIENTID, 'value'),
           State(ids.APIMQTTUSERNAME, 'value'),
           State(ids.APIMQTTPASSWORD, 'value'),
           State(ids.APIMQTTSERVER, 'value'),
           State(ids.APIMQTTPORT, 'value'),
           State(ids.APIMQTTCASSANDRASERVERNAME, 'value'),
           State(ids.RADIOMESSAGESERVICETYPE, 'value'),
           State(ids.TELEGRAMTOKEN, 'value'),
           State(ids.TELEGRAMCHATID, 'value'),
           State(ids.PUSHOVERTOKEN, 'value'),
           State(ids.PUSHOVERUSER, 'value'),
           ])
def update_connection_data(bsr_n_clicks: int, 
                           bok_n_clicks: int,
                           is_open: bool, 
                           connectiontype: str,
                           mqttclientid: str, 
                           mqttusername: str, 
                           mqttpassword: str, 
                           mqttserver: str, 
                           mqttport: int, 
                           mqttrovername: str, 
                           ipadressrover: str, 
                           sunraypass: str,
                           serport: str, 
                           baudrate: int,
                           apiconnectiontype: str,
                           apimqttclientid: str,
                           apimqttusername: str,
                           apimqttpassword: str,
                           apimqttserver: str,
                           apimqttport: int,
                           apicassandraservername: str,
                           messageservicetype: str,
                           telegramtoken: str,
                           telegramchatid: str,
                           pushovertoken: str,
                           pushoveruser: str,
                           ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOK:
        if connectiontype == 'MQTT':
            commcfg.use = connectiontype
            commcfg.mqtt_client_id = mqttclientid
            commcfg.mqtt_username = mqttusername
            commcfg.mqtt_pass = mqttpassword
            commcfg.mqtt_port = mqttport
            commcfg.mqtt_mower_name = mqttrovername
        if connectiontype == 'HTTP':
            commcfg.use = connectiontype
            commcfg.http_ip = ipadressrover
            commcfg.http_pass = sunraypass
        if connectiontype == 'UART':
            commcfg.use = connectiontype
            commcfg.uart_port = serport
            commcfg.uart_baudrate = baudrate
        if apiconnectiontype == 'deactivated':
            commcfg.api = None
        if apiconnectiontype == 'MQTT':
            commcfg.api = 'MQTT'
            commcfg.api_mqtt_client_id = apimqttclientid
            commcfg.api_mqtt_username = apimqttusername
            commcfg.api_mqtt_pass = apimqttpassword
            commcfg.api_mqtt_server = apimqttserver
            commcfg.api_mqtt_port = apimqttport
            commcfg.api_mqtt_cassandra_server_name = apicassandraservername
        if messageservicetype == 'deactivated':
            commcfg.message_service = None
            commcfg.telegram_token = None
            commcfg.telegram_chat_id = None
            commcfg.pushover_token = None
            commcfg.pushover_user = None
        if messageservicetype == 'Telegram':
            commcfg.message_service = 'Telegram'
            commcfg.telegram_token = telegramtoken
            try:
                commcfg.telegram_chat_id = int(telegramchatid)
            except:
                commcfg.telegram_chat_id = None
        if messageservicetype == 'Pushover':
            commcfg.message_service = 'Pushover'
            commcfg.pushover_token = pushovertoken
            commcfg.pushover_user = pushoveruser
        
        commcfg.save_commcfg()
        backendserver.reboot()
        return False

    if context == ids.BUTTONSAVEANDREBOOT:
        return True
    return False

@callback(Output(ids.POSITIONMODESTYLE, 'style'),
          Input(ids.RADIOPOSITIONMODE, 'value'))
def update_connectioninput(radio_input: str) -> list:
    if radio_input == 'absolute':
        return {'display': 'block'}
    else:
        return {'display': 'none'}
    
@callback(Output(ids.MODALMAPSETTINGS, 'is_open'),
          [Input(ids.BUTTONSAVEMAPSETTINGS, 'n_clicks'),
           Input(ids.BUTTONOKMAPSETTINGS, 'n_clicks'),
           State(ids.MODALMAPSETTINGS, 'is_open'),
           State(ids.MOWOFFSETSETTINGS, 'value'),
           State(ids.MOWANGLESETTINGS, 'value'),
           State(ids.MOWEDGESETTINGS, 'value'),
           State(ids.DISTANCETOBORDERSETTINGS, 'value'),
           State(ids.PATTERNSETTINGS, 'value'),
           State(ids.MOWAREASETTINGS, 'value'),
           State(ids.MOWEDGEEXCLUSIONSETTINGS, 'value'),
           State(ids.MOWBORDERCCWSETTINGS, 'value')])
def update_pathplanner_settings_data(bsr_n_clicks: int, 
                                     bok_n_clicks: int, 
                                     is_open: bool, 
                                     mowoffset: float, 
                                     mowangle: int, 
                                     mowedge: str, 
                                     distancetoborder: int, 
                                     pattern: str,
                                     mowarea: bool, 
                                     mowexclusion: bool,
                                     mowborderccw: bool
                                     ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKMAPSETTINGS:
        pathplannercfg.pattern = pattern
        if mowoffset != None:
            pathplannercfg.width = mowoffset
        pathplannercfg.angle = mowangle
        if distancetoborder != None:
            pathplannercfg.distancetoborder = distancetoborder
        pathplannercfg.mowarea = mowarea
        pathplannercfg.mowborder = mowedge
        pathplannercfg.mowexclusion = mowexclusion
        pathplannercfg.mowborderccw = mowborderccw
        pathplannercfg.save_pathplannercfg()
    if bsr_n_clicks or bok_n_clicks:
        return not is_open
    return is_open

@callback(Output(ids.MODALAPPSETTINGS, 'is_open'),
          [Input(ids.BUTTONSAVEAAPPSETTINGS, 'n_clicks'),
           Input(ids.BUTTONOKAPPSETTINGS, 'n_clicks'),
           State(ids.MODALAPPSETTINGS, 'is_open'),
           State(ids.MAXAGESETTINGS, 'value'),
           State(ids.TIMETOOFFLINESETTINGS, 'value'),
           State(ids.CURRENTTHDCHARGESETTINGS, 'value'),
           State(ids.VOLTAGEMINSETTINGS, 'value'),
           State(ids.VOLTAGEMAXSETTINGS, 'value'),
           State(ids.ROVERPICTURESETTINGS, 'value'),
           State(ids.MAXAMOUNTOBSTACLESSETTINGS, 'value'),
           State(ids.LIGHTMODESETTINGS, 'value'),
           ])
def update_app_data(bsr_n_clicks: int, 
                    bok_n_clicks: int, 
                    is_open: bool, 
                    maxage: int, 
                    timetooffline: int, 
                    currentthd: float,
                    voltagemin: float, 
                    voltagemax: float, 
                    roverpicture: str,
                    maxobstacles: int,
                    lightmode: str,
                    ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKAPPSETTINGS:
        if maxage != None:
            appcfg.datamaxage = maxage
        if timetooffline != None:
            appcfg.time_to_offline = timetooffline
        if currentthd != None:
            appcfg.current_thd_charge = currentthd
        if voltagemin != None:
            appcfg.voltage_0 = voltagemin
        if voltagemax != None:
            appcfg.voltage_100 = voltagemax
        if maxobstacles != None:
            appcfg.obstacles_amount = maxobstacles
        if lightmode != None:
            appcfg.light_mode = True if lightmode == "True" else False
        appcfg.rover_picture = roverpicture
        appcfg.save_appcfg()
        appcfg.read_appcfg()
    if bsr_n_clicks or bok_n_clicks:
        return not is_open
    return is_open

@callback(Output(ids.ROVERPICTUREPREVIEWSETTINGS, 'src'),
          [Input(ids.ROVERPICTURESETTINGS, 'value'),
           State(ids.ROVERPICTURESETTINGS, 'value')])
def update_rover_picture_preview(preview_picture: str, preview_picture_state: str) -> str:
    return appcfg.show_preview_image(preview_picture_state)
    #return preview_picture_state

@callback(Output(ids.MODALROBOTSETTINGS, 'is_open'),
          Input(ids.BUTTONSAVEROBOTSETTINGS, 'n_clicks'),
          Input(ids.BUTTONOKROBOTSETTINGS, 'n_clicks'),
          State(ids.MODALROBOTSETTINGS, 'is_open'),
          State(ids.MOWSPEEDSETPOINTSETTINGS, 'value'),
          State(ids.GOTOSPEEDSETPOINTSETTINSGS, 'value'),
          State(ids.RADIOPOSITIONMODE, 'value'),
          State(ids.POSITIONMODELON, 'value'),
          State(ids.POSITIONMODELAT, 'value'),
          State(ids.FIXTIMEOUTSETTINGS, 'value'),
          )
def update_robotsettings_data(
                    bsrs_nclicks: int, 
                    bok_nclicks: int, 
                    is_open: bool, 
                    mowspeedsetpoint: float, 
                    gotospeedsetpoint: float,
                    positionmode: str, 
                    positionmodelon: float, 
                    positionmodelat: float,
                    fixtimeout: int,
                    ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKROBOTSETTINGS:
        rovercfg.mowspeed_setpoint = mowspeedsetpoint
        rovercfg.gotospeed_setpoint = gotospeedsetpoint
        rovercfg.positionmode = positionmode
        rovercfg.lon = positionmodelon
        rovercfg.lat = positionmodelat
        rovercfg.fix_timeout = fixtimeout
        res = rovercfg.save_rovercfg()
        cmdlist.cmd_set_positionmode = True
    if bsrs_nclicks or bok_nclicks:
        return not is_open
    return is_open

@callback(Output(ids.APINONECONNECTIONSTYLE, 'style'),
          Output(ids.APIMQTTCONNECTIONSTYLE, 'style'),
          [Input(ids.RADIOAPICONNECTIONTYPE, 'value'),
           ])
def update_apiconnectioninput(radio_input: str,
                              ) -> list:
    if radio_input == 'deactivated':
        return {'display': 'none'}, {'display': 'none'}
    elif radio_input == 'MQTT':
        return {'display': 'none'}, {'display': 'block'}
    else:
        return {'display': 'none'}, {'display': 'none'}

@callback(Output(ids.MESSAGESERVICESTYLE, 'style'),
          Output(ids.TELEGRAMSERVICESTYLE, 'style'),
          Output(ids.PUSHOVERSERVICESTYLE, 'style'),
          [Input(ids.RADIOMESSAGESERVICETYPE, 'value')],
          )
def update_messageservicetype(radio_input: str,
                              ) -> list:
    if radio_input == 'deactivated':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
    elif radio_input == 'Telegram':
        return {'display': 'none'}, {'display': 'block'}, {'display': 'none'}
    elif radio_input == 'Pushover':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'block'}
    else:
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'} 

@callback(Output(ids.RADIOPOSITIONMODE, 'value'),
          Output(ids.POSITIONMODELON, 'value'),
          Output(ids.POSITIONMODELAT, 'value'),
          Output(ids.MOWSPEEDSETPOINTSETTINGS, 'value'),
          Output(ids.GOTOSPEEDSETPOINTSETTINSGS, 'value'),
          Output(ids.FIXTIMEOUTSETTINGS, 'value'),
          [Input(ids.URLUPDATE, 'pathname')])
def update_robotsettings_on_reload(pathname: str) -> list:
    return rovercfg.positionmode, rovercfg.lon, rovercfg.lat, rovercfg.mowspeed_setpoint, rovercfg.gotospeed_setpoint, rovercfg.fix_timeout

@callback(Output(ids.MOWOFFSETSETTINGS, 'value'),
          Output(ids.MOWANGLESETTINGS, 'value'),
          Output(ids.MOWEDGESETTINGS, 'value'),
          Output(ids.DISTANCETOBORDERSETTINGS, 'value'),
          Output(ids.PATTERNSETTINGS, 'value'),
          Output(ids.MOWAREASETTINGS, 'value'),
          Output(ids.MOWEDGEEXCLUSIONSETTINGS, 'value'),
          Output(ids.MOWBORDERCCWSETTINGS, 'value'),
          [Input(ids.URLUPDATE, 'pathname')])
def update_pathplandersettings_on_reload(pathname: str) -> list:
    return pathplannercfg.width, pathplannercfg.angle, pathplannercfg.mowborder, pathplannercfg.distancetoborder, pathplannercfg.pattern, pathplannercfg.mowarea, pathplannercfg.mowexclusion, pathplannercfg.mowborderccw

@callback(Output(ids.MAXAGESETTINGS, 'value'),
          Output(ids.TIMETOOFFLINESETTINGS, 'value'),
          Output(ids.CURRENTTHDCHARGESETTINGS, 'value'),
          Output(ids.VOLTAGEMINSETTINGS, 'value'),
          Output(ids.VOLTAGEMAXSETTINGS, 'value'),
          Output(ids.ROVERPICTURESETTINGS, 'value'),
          Output(ids.MAXAMOUNTOBSTACLESSETTINGS, 'value'),
          Output(ids.LIGHTMODESETTINGS, 'value'),
          [Input(ids.URLUPDATE, 'pathname')])
def update_appsettings_on_reload(pathname: str) -> list:
    return appcfg.datamaxage, appcfg.time_to_offline, appcfg.current_thd_charge, appcfg.voltage_0, appcfg.voltage_100, appcfg.rover_picture, appcfg.obstacles_amount, str(appcfg.light_mode)
  
@callback(Output(ids.BUTTONSENDTELEGRAMMESSAGE, 'active'),
          [Input(ids.BUTTONSENDTELEGRAMMESSAGE, 'n_clicks'),
          State(ids.TELEGRAMTESTMESSAGE, 'value'),
          ])
def send_test_message(bsm_nclicks: int,
                      message: str,
                      ) -> bool:
    if bsm_nclicks:
        messageservice.send_message(message)
    return False