import sys
import os
import pytest
import json
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.comm.apitopics.mowparameterstopic import MowParametersTopic

@pytest.fixture
def mowParametersTopic():
    return MowParametersTopic()

def test_createPayload(mowParametersTopic):
    mowParametersTopic.createPayload()
    expected_payload = {
        'mowPattern': 'lines',
        'width': 0.18,
        'angle': 0,
        'distanceToBorder': 1,
        'mowArea': True,
        'borderLaps': 1,
        'mowExclusionBorder': True,
        'mowBorderCcw': True
    }

    assert json.loads(mowParametersTopic.mowParametersStateJson) == expected_payload

if __name__ == '__main__':
    pytest.main()