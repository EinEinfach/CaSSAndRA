import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
import json

from ...data.cfgdata import pathplannercfgapi


@dataclass
class MowParametersTopic:
    mowParametersState: dict = field(default_factory=dict)
    mowParametersStateJson: str = '{}'

    def createPayload(self) -> dict:
        try:
            self.mowParametersState['pattern'] = pathplannercfgapi.pattern
            self.mowParametersState['width'] = pathplannercfgapi.width
            self.mowParametersState['angle'] = pathplannercfgapi.angle
            self.mowParametersState['distancetoborder'] = pathplannercfgapi.distancetoborder
            self.mowParametersState['mowarea'] = pathplannercfgapi.mowarea
            self.mowParametersState['mowborder'] = pathplannercfgapi.mowborder
            self.mowParametersState['mowexclusion'] = pathplannercfgapi.mowexclusion
            self.mowParametersState['mowborderccw'] = pathplannercfgapi.mowborderccw
            self.mowParametersStateJson = json.dumps(self.mowParametersState)
            return self.mowParametersStateJson
        except Exception as e:
            logger.error('Could not create api mow parameters payload.')
            logger.error(str(e))
            return dict()

mowParametersTopic = MowParametersTopic()
