import logging
logger = logging.getLogger(__name__)

# imports
from dataclasses import dataclass, field

@dataclass
class PathData:
    file_paths = None
    data: str = ''
    log: str = ''
    src: str = ''

    def set(self, file_paths) -> None:
        self.file_paths = file_paths
        self.data = file_paths.data
        self.log = file_paths.log
        self.src = file_paths.src

paths = PathData()