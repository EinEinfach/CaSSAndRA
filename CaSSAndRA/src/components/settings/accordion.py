from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import time

from .. import ids
from . import buttons
from src.backend import backendserver
from src.backend.comm import cfg
from src.backend.data import appdata, mapdata
from src.backend.data.cfgdata import rovercfg, pathplannercfg
from src.backend.comm import cmdlist

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
                                        dbc.Input(value = appdata.commcfg['MQTT'][0]['CLIENT_ID'], className='mb-3', id=ids.MQTTCLIENTID),
                                        dbc.FormText('Username'),
                                        dbc.Input(placeholder='your MQTT-Server username, leave empty if not in use', className='mb-3', id=ids.MQTTUSERNAME),
                                        dbc.FormText('Password'),
                                        dbc.Input(placeholder='your MQTT-Server password, leave empty if not in use', className='mb-3', id=ids.MQTTPASSWORD),
                                        dbc.FormText('MQTT-Server'),
                                        dbc.Input(value = appdata.commcfg['MQTT'][3]['MQTT_SERVER'], className='mb-3', id=ids.MQTTSERVER),
                                        dbc.FormText('Port'),
                                        dbc.Input(value = appdata.commcfg['MQTT'][4]['PORT'], className='mb-3', id=ids.MQTTPORT, type='number'),
                                        dbc.FormText('Mower name with prefix'),
                                        dbc.Input(value = appdata.commcfg['MQTT'][5]['MOWER_NAME'], className='mb-3', id=ids.MQTTROVERNAME)  
                                    ], id=ids.MQTTCONNECTIONSTYLE),

                                    html.Div([dbc.FormText('IP-Adress of your rover'),
                                        dbc.Input(value = appdata.commcfg['HTTP'][0]['IP'], className='mb-3', id=ids.IPADRESSROVER),
                                        dbc.FormText('Connection password (see your config.h)'),
                                        dbc.Input(placeholder='see config.h of sunray FW', className='mb-3', id=ids.SUNRAYPASS),
                                    ], id=ids.HTTPCONNECTIONSTYLE),

                                    html.Div([dbc.FormText('Serial port'),
                                        dbc.Input(value = appdata.commcfg['UART'][0]['SERPORT'], className='mb-3', id=ids.SERPORT),
                                        dbc.FormText('Baudrate'),
                                        dbc.Input(value = appdata.commcfg['UART'][1]['BAUDRATE'], className='mb-3', id=ids.BAUDRATE, type='number'),
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
                                dbc.Input(value=pathplannercfg.width, className='mb-3', id=ids.MOWOFFSETSETTINGS, type='number', min=0.01, max=1, step=0.01),
                                dbc.FormText('Mow angle'),
                                dbc.Input(value=pathplannercfg.angle, className='mb-3', id=ids.MOWANGLESETTINGS, type='number', min=0, max=359, step=1),
                                dbc.FormText('Distance to border'),
                                dbc.Input(value=pathplannercfg.distancetoborder, className='mb-3', id=ids.DISTANCETOBORDERSETTINGS, type='number', min=0, max=5, step=1),
                                dbc.FormText('Mow area'),
                                dbc.Select(
                                    id=ids.MOWAREASETTINGS,
                                    options=[
                                        {'label': 'yes', 'value': 'yes'},
                                        {'label': 'no', 'value': 'no'},
                                    ],
                                    value=pathplannercfg.mowarea
                                ),
                                dbc.FormText('Mow cut edge border'),
                                dbc.Select(
                                    id=ids.MOWEDGESETTINGS,
                                    options=[
                                        {'label': 'yes', 'value': 'yes'},
                                        {'label': 'no', 'value': 'no'},
                                    ],
                                    value=pathplannercfg.mowborder
                                ),
                                dbc.FormText('Mow cut edge exclusion'),
                                dbc.Select(
                                    id=ids.MOWEDGEEXCLUSIONSETTINGS,
                                    options=[
                                        {'label': 'yes', 'value': 'yes'},
                                        {'label': 'no', 'value': 'no'},
                                    ],
                                    value=pathplannercfg.mowexclusion
                                ),
                                dbc.FormText('Mow cut edge border in ccw'),
                                dbc.Select(
                                    id=ids.MOWBORDERCCWSETTINGS,
                                    options=[
                                        {'label': 'yes', 'value': 'yes'},
                                        {'label': 'no', 'value': 'no'},
                                    ],
                                    value=pathplannercfg.mowborderccw
                                ),
                            ],
                            title='Coverage path planner',
                        ),
                        dbc.AccordionItem(
                            [
                            html.P('Settings for calculation inside the app'),
                            html.Div(buttons.savebuttonappsettings),
                            dbc.FormText('Max age for measured data [days]'),
                            dbc.Input(value=appdata.datamaxage, className='mb-3', type='number', min=1, step=1, id=ids.MAXAGESETTINGS),
                            dbc.FormText('Time to wait before offline [s]'),
                            dbc.Input(value=appdata.time_to_offline, className='mb-3', type='number', min=30, step=1, id=ids.TIMETOOFFLINESETTINGS),
                            dbc.FormText('Min charge current [A]'),
                            dbc.Input(value=appdata.current_thd_charge, className='mb-3', type='number', max=0, step=0.01, id=ids.CURRENTTHDCHARGESETTINGS),
                            dbc.FormText('Voltage [V] to SoC [%]'),
                            dbc.Row([
                                dbc.Col([
                                    dbc.FormText('Voltage min (0% SoC)'),
                                    dbc.Input(value=appdata.soc_lookup_table[0]['V'], className='mb-3', type='number', min=0, step=0.1, id=ids.VOLTAGEMINSETTINGS),
                                ]),   
                                dbc.Col([
                                    dbc.FormText('Voltage max (100% SoC)'),
                                    dbc.Input(value=appdata.soc_lookup_table[1]['V'], className='mb-3', type='number', min=0, step=0.1, id=ids.VOLTAGEMAXSETTINGS),
                                ]),                         
                            ]),
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
                                        value=mapdata.positionmode,
                                        id=ids.RADIOPOSITIONMODE,
                                        inline=True
                                    ), 
                                ]),
                                html.Div([
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.FormText('Lon'),
                                            dbc.Input(value=mapdata.lon, className='mb-3', id=ids.POSITIONMODELON, type='number'),
                                        ]),
                                        dbc.Col([
                                            dbc.FormText('Lat'),
                                            dbc.Input(value=mapdata.lat, className='mb-3', id=ids.POSITIONMODELAT, type='number'),
                                        ]),
                                    ]),
                                ], id=ids.POSITIONMODESTYLE),
                            dbc.FormText('Default mow speed setpoint [m/s]'),
                            dbc.Input(value=rovercfg.mowspeed_setpoint, className='mb-3', type='number', min=0.1, max=1.0, step=0.01, id=ids.MOWSPEEDSETPOINTSETTINGS),
                            dbc.FormText('Default transit speed setpoint [m/s]'),
                            dbc.Input(value=rovercfg.gotospeed_setpoint, className='mb-3', type='number', min=0.1, max=1.0, step=0.01, id=ids.GOTOSPEEDSETPOINTSETTINSGS),
                        ], title='Robot'),
                    ], start_collapsed=True, id=ids.ACCORDIONSETTINGS
                )

@callback(Output(ids.MQTTCONNECTIONSTYLE, 'style'),
          Output(ids.HTTPCONNECTIONSTYLE, 'style'),
          Output(ids.UARTCONNECTIONSTYLE, 'style'),
          Input(ids.RADIOCONNECTIONTYPE, 'value'))
def update_connectioninput(radio_input: str()) -> list(dict()):
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
           State(ids.BAUDRATE, 'value')])
def update_connection_data(bsr_n_clicks: int, bok_n_clicks: int,
                           is_open: bool, connectiontype: str(),
                           mqttclientid: str(), mqttusername: str(), mqttpassword: str(), mqttserver: str(), mqttport: int(), mqttrovername: str(), 
                           ipadressrover: str(), sunraypass: str(),
                           serport: str(), baudrate: int()) -> bool():
    context = ctx.triggered_id
    if context == ids.BUTTONOK:
        if connectiontype == 'MQTT':
            mqtt_connect_data = {'USE': connectiontype, 'CLIENT_ID': mqttclientid, 
                                 'USERNAME': mqttusername, 'PASSWORD': mqttpassword, 
                                 'MQTT_SERVER': mqttserver, 'PORT': mqttport, 
                                 'MOWER_NAME': mqttrovername}
            cfg.save_commcfg(mqtt_connect_data)
            backendserver.stop()
        elif connectiontype == 'HTTP':
            http_connect_data = {'USE': connectiontype, 'IP': ipadressrover, 'PASSWORD': sunraypass}
            cfg.save_commcfg(http_connect_data)
            backendserver.stop()
        elif connectiontype == 'UART':
            uart_connect_data = {'USE': connectiontype, 'SERPORT': serport, 'BAUDRATE': baudrate}
            cfg.save_commcfg(uart_connect_data)
            backendserver.stop()

    if bsr_n_clicks or bok_n_clicks:
        return not is_open
    return is_open

@callback(Output(ids.POSITIONMODESTYLE, 'style'),
          Input(ids.RADIOPOSITIONMODE, 'value'))
def update_connectioninput(radio_input: str()) -> list(dict()):
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
def update_pathplanner_settings_data(bsr_n_clicks: int, bok_n_clicks: int, 
                                     is_open: bool, mowoffset: float, 
                                     mowangle: int, mowedge: str, 
                                     distancetoborder: int, pattern: str,
                                     mowarea: str, mowexclusion: str,
                                     mowborderccw: str) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKMAPSETTINGS:
        pathplannercfg.pattern = pattern
        if mowoffset != None:
            pathplannercfg.width = mowoffset
        if mowangle != None:
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
          [Input(ids.BUTTONSAVEANDREBOOTAPPSETTINGS, 'n_clicks'),
           Input(ids.BUTTONOKAPPSETTINGS, 'n_clicks'),
           State(ids.MODALAPPSETTINGS, 'is_open'),
           State(ids.MAXAGESETTINGS, 'value'),
           State(ids.TIMETOOFFLINESETTINGS, 'value'),
           State(ids.CURRENTTHDCHARGESETTINGS, 'value'),
           State(ids.VOLTAGEMINSETTINGS, 'value'),
           State(ids.VOLTAGEMAXSETTINGS, 'value')])
def update_app_data(bsr_n_clicks: int, bok_n_clicks: int, is_open: bool, 
                    maxage: int, timetooffline: int, currentthd: float,
                    voltagemin: float, voltagemax: float) -> bool():
    context = ctx.triggered_id
    if context == ids.BUTTONOKAPPSETTINGS:
        appdata = {'datamaxage': maxage, 'time_to_offline': timetooffline, 'current_thd_charge': currentthd,
                   'voltage_to_soc': [{'V': voltagemin, 'SoC': 0}, {'V': voltagemax, 'SoC': 100}]}

        cfg.save_appcfg(appdata)
        backendserver.stop()
    if bsr_n_clicks or bok_n_clicks:
        return not is_open
    return is_open

@callback(Output(ids.MODALROBOTSETTINGS, 'is_open'),
          Input(ids.BUTTONSAVEROBOTSETTINGS, 'n_clicks'),
          Input(ids.BUTTONOKROBOTSETTINGS, 'n_clicks'),
          State(ids.MODALROBOTSETTINGS, 'is_open'),
          State(ids.MOWSPEEDSETPOINTSETTINGS, 'value'),
          State(ids.GOTOSPEEDSETPOINTSETTINSGS, 'value'),
          State(ids.RADIOPOSITIONMODE, 'value'),
          State(ids.POSITIONMODELON, 'value'),
          State(ids.POSITIONMODELAT, 'value'))
def update_robotsettings_data(bsrs_nclicks: int, bok_nclicks: int, is_open: bool, 
                      mowspeedsetpoint: float, gotospeedsetpoint: float,
                      positionmode: str(), positionmodelon: float, positionmodelat: float
                      ) -> bool:
    context = ctx.triggered_id
    if context == ids.BUTTONOKROBOTSETTINGS:
        rovercfg.mowspeed_setpoint = mowspeedsetpoint
        rovercfg.gotospeed_setpoint = gotospeedsetpoint
        rovercfg.positionmode = positionmode
        rovercfg.lon = positionmodelon
        rovercfg.lat = positionmodelat
        res = rovercfg.save_rovercfg()
        cmdlist.cmd_set_positionmode = True
    if bsrs_nclicks or bok_nclicks:
        return not is_open
    return is_open

@callback(Output(ids.RADIOPOSITIONMODE, 'value'),
          Output(ids.POSITIONMODELON, 'value'),
          Output(ids.POSITIONMODELAT, 'value'),
          Output(ids.MOWSPEEDSETPOINTSETTINGS, 'value'),
          Output(ids.GOTOSPEEDSETPOINTSETTINSGS, 'value'),
          [Input(ids.URLUPDATE, 'pathname')])
def update_robotsettings_on_reload(pathname: str) -> list:
    return rovercfg.positionmode, rovercfg.lon, rovercfg.lat, rovercfg.mowspeed_setpoint, rovercfg.gotospeed_setpoint

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
    
  
   