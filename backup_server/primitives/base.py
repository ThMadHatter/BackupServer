from abc import ABC, abstractmethod
from typing import Any, Dict, List
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

class PrimitiveContract(BaseModel):
    inputs: List[str]
    outputs: List[str]
    side_effects: List[str]
    failure_modes: List[str]
    retryable: bool
    idempotent: bool

class Primitive(ABC):
    contract: PrimitiveContract

    def __init__(self, name: str, options: Dict[str, Any]):
        self.name = name
        self.options = options
        self.logger = logger.bind(primitive=self.__class__.__name__, name=name)

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        pass
