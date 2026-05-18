from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

logger = structlog.get_logger()

class Primitive(ABC):
    def __init__(self, name: str, options: Dict[str, Any]):
        self.name = name
        self.options = options
        self.logger = logger.bind(primitive=self.__class__.__name__, name=name)

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        pass
