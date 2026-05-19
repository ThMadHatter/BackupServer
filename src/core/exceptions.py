class BackupEngineError(Exception):
    """Base exception for all backup engine errors."""
    pass

class ConfigError(BackupEngineError):
    """Raised when there is an issue with the configuration."""
    pass

class CatalogError(BackupEngineError):
    """Raised when there is an issue with the catalog."""
    pass

class StorageError(BackupEngineError):
    """Raised when there is an issue with storage operations."""
    pass

class PrimitiveError(BackupEngineError):
    """Raised when a primitive execution fails."""
    pass

class RestoreSafetyError(BackupEngineError):
    """Raised when a restore operation is deemed unsafe."""
    pass
