import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from jinja2 import Template

class StepSpec(BaseModel):
    name: str
    type: str
    options: Dict[str, Any] = {}
    register: Optional[str] = None
    retry: Optional[int] = 0
    timeout: Optional[int] = None
    ignore_errors: bool = False

class ServiceSpec(BaseModel):
    name: str
    backup: List[StepSpec]
    restore: Optional[List[StepSpec]] = None
    validation: Optional[List[StepSpec]] = None

def load_spec(path: Path, variables: Dict[str, Any] = {}) -> ServiceSpec:
    with open(path, "r") as f:
        content = f.read()

    # Template the YAML before parsing
    template = Template(content)
    rendered = template.render(**variables)

    data = yaml.safe_load(rendered)
    return ServiceSpec(**data)
