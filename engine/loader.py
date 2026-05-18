import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from jinja2 import Template
from enum import Enum

class ConsistencyLevel(str, Enum):
    CRASH_CONSISTENT = "crash_consistent"
    APPLICATION_CONSISTENT = "application_consistent"
    EVENTUAL_CONSISTENT = "eventual_consistent"

class StepSpec(BaseModel):
    name: str
    type: str
    options: Dict[str, Any] = {}
    register: Optional[str] = None
    retry: Optional[int] = 0
    timeout: Optional[int] = None
    ignore_errors: bool = False
    depends_on: List[str] = Field(default_factory=list)

class HookSpec(BaseModel):
    pre_backup: List[StepSpec] = Field(default_factory=list)
    post_backup: List[StepSpec] = Field(default_factory=list)
    pre_restore: List[StepSpec] = Field(default_factory=list)
    post_restore: List[StepSpec] = Field(default_factory=list)
    on_failure: List[StepSpec] = Field(default_factory=list)

class ServiceSpec(BaseModel):
    name: str
    schema_version: str = "1.0"
    consistency: ConsistencyLevel = ConsistencyLevel.CRASH_CONSISTENT
    backup: List[StepSpec]
    restore: Optional[List[StepSpec]] = None
    validation: Optional[List[StepSpec]] = None
    hooks: HookSpec = Field(default_factory=HookSpec)

def load_spec(path: Path, variables: Dict[str, Any] = {}) -> ServiceSpec:
    with open(path, "r") as f:
        content = f.read()

    # Template the YAML before parsing
    template = Template(content)
    rendered = template.render(**variables)

    data = yaml.safe_load(rendered)
    return ServiceSpec(**data)
