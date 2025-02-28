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
            self.mowParametersState['mowPattern'] = pathplannercfgapi.pattern
            self.mowParametersState['width'] = pathplannercfgapi.width
            self.mowParametersState['angle'] = pathplannercfgapi.angle
            self.mowParametersState['distanceToBorder'] = pathplannercfgapi.distancetoborder
            self.mowParametersState['mowArea'] = pathplannercfgapi.mowarea
            self.mowParametersState['borderLaps'] = pathplannercfgapi.mowborder
            self.mowParametersState['mowExclusionBorder'] = pathplannercfgapi.mowexclusion
            self.mowParametersState['mowBorderCcw'] = pathplannercfgapi.mowborderccw
            self.mowParametersStateJson = json.dumps(self.mowParametersState)
            return self.mowParametersStateJson
        except Exception as e:
            logger.error('Could not create api mow parameters payload.')
            logger.error(str(e))
            return dict()

mowParametersTopic = MowParametersTopic()
