from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class ExecutionContext(BaseModel):
    run_id: str
    timestamp: datetime
    service: str
    staging_dir: Path
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False

    # Backward compatibility and convenient access
    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["timestamp"] = self.timestamp.strftime("%Y%m%d_%H%M%S")
        d["staging_dir"] = str(self.staging_dir)
        # Merge variables into top level for Jinja2 templates as before
        return {**d, **self.variables}
