import sys
import os
import pytest
import json
from unittest.mock import patch, call

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.comm.apitopics.robottopic import RobotTopic

@pytest.fixture
def robotTopic():
    return RobotTopic()

def test_checkCmd_valid(robotTopic):
    for cmd in robotTopic.allowedCmds:
        with patch('src.backend.comm.apitopics.robottopic.robotInterface.performCmd') as mock_performCmd, \
            patch('src.backend.comm.apitopics.robottopic.path') as mock_path:
            if cmd == 'mow':
                robotTopic.checkCmd(buffer={'command': cmd, 'value': ['resume']})
                mock_performCmd.assert_called_with('resume')
                robotTopic.checkCmd(buffer={'command': cmd, 'value': ['task']})
                mock_performCmd.assert_called_with('mow')
                robotTopic.checkCmd(buffer={'command': cmd, 'value': ['all']})
                mock_performCmd.assert_called_with('mow')
            elif cmd == 'move':
                robotTopic.checkCmd(buffer={'command': cmd, 'value': [0.1, 0.11]})
                mock_performCmd.assert_called_with('move')
            elif cmd == 'setMowSpeed' or cmd == 'setGoToSpeed' or cmd == 'setMowProgress':
                robotTopic.checkCmd(buffer={'command': cmd, 'value': [0.5]})
            elif cmd == 'goTo':
                robotTopic.checkCmd(buffer={'command': cmd, 'value': {'x': [0.5], 'y': [0.5]}})
                mock_performCmd.assert_called_with('goTo')
            elif cmd == 'skipNextPoint':
                robotTopic.checkCmd(buffer={'command': cmd, 'value': []})
                expected_calls = [call('stop'), call('skipNextPoint'), call('resume')]
                mock_performCmd.assert_has_calls(expected_calls, any_order=False)
            else:
                robotTopic.checkCmd(buffer={'command': cmd, 'value': []})
                mock_performCmd.assert_called_with(cmd)

def test_checkCmd_invalid(robotTopic):
    with patch('src.backend.comm.apitopics.robottopic.logger') as mock_logger:
        robotTopic.checkCmd(buffer={'command': ''})
        mock_logger.info.assert_called_with(f'No valid command in api message for robot topic found. Allowed commands: {robotTopic.allowedCmds}. Aborting')
        robotTopic.checkCmd(buffer={'command': 'invalid'})
        mock_logger.info.assert_called_with(f'No valid command in api message for robot topic found. Allowed commands: {robotTopic.allowedCmds}. Aborting')
        robotTopic.checkCmd(buffer={})
        expected_calls = [call.error('Api command for robot topic is invalid'), call.error("'command'")]
        mock_logger.assert_has_calls(expected_calls, any_order=False)

def test_createPayload(robotTopic):
    with patch('src.backend.comm.apitopics.robottopic.robot') as mock_robot:
        mock_robot.fw = '1.0.0'
        mock_robot.fw_version = '1.0.0'
        mock_robot.status = 'active'
        mock_robot.dock_reason = ''
        mock_robot.sensor_status = ''
        mock_robot.soc = 100
        mock_robot.battery_voltage = 27.0
        mock_robot.amps = 1.5
        mock_robot.position_x = 10.0
        mock_robot.position_y = 20.0
        mock_robot.target_x = 15.0
        mock_robot.target_y = 25.0
        mock_robot.position_delta = 5.0
        mock_robot.position_mow_point_index = 1
        mock_robot.position_visible_satellites = 10
        mock_robot.position_visible_satellites_dgps = 5
        mock_robot.position_age_hr = 0.1
        mock_robot.solution = 'fix'
        mock_robot.seconds_per_idx = 60
        mock_robot.speed = 1.0
        mock_robot.average_speed = 1.2
        mock_robot.last_mow_status = True

        robotTopic.createPayload()

        expected_payload = {
            'firmware': '1.0.0',
            'version': '1.0.0',
            'status': 'active',
            'dockReason': '',
            'sensorState': '',
            'battery': {'soc': 100, 'voltage': 27.0, 'electricCurrent': 1.5},
            'position': {'x': 10.0, 'y': 20.0},
            'target': {'x': 15.0, 'y': 25.0},
            'angle': 5.0,
            'mowPointIdx': 1,
            'gps': {'visible': 10, 'dgps': 5, 'age': 0.1, 'solution': 'fix'},
            'secondsPerIdx': 60,
            'speed': 1.0,
            'averageSpeed': 1.2,
            'mowMotorActive': True
        }

        assert robotTopic.robotstate == expected_payload
        assert json.loads(robotTopic.robotstateJson) == expected_payload

if __name__ == '__main__':
    pytest.main()