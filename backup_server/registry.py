from typing import Dict, Type, List
from backup_server.modules.base import BackupModule
import importlib
import structlog

logger = structlog.get_logger()

class ModuleRegistry:
    def __init__(self):
        self._modules: Dict[str, Type[BackupModule]] = {}

    def register(self, name: str, module_class: Type[BackupModule]):
        self._modules[name] = module_class
        logger.info("Module registered", module=name)

    def get_module(self, name: str) -> Type[BackupModule]:
        if name not in self._modules:
            raise KeyError(f"Module '{name}' not found in registry")
        return self._modules[name]

    def list_modules(self) -> List[str]:
        return list(self._modules.keys())

    def discover_modules(self):
        # Dynamically load modules from backup_server/modules
        # For now, we'll manually register them or use a decorator
        pass

registry = ModuleRegistry()

def register_module(name: str):
    def decorator(cls: Type[BackupModule]):
        registry.register(name, cls)
        return cls
    return decorator
