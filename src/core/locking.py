import fcntl
import os
from pathlib import Path
import structlog

logger = structlog.get_logger()

class Lock:
    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.handle = None

    def acquire(self):
        self.handle = open(self.lock_file, "w")
        try:
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logger.info("Lock acquired", path=str(self.lock_file))
        except IOError:
            logger.error("Failed to acquire lock. Another instance might be running.", path=str(self.lock_file))
            raise RuntimeError("Could not acquire lock")

    def release(self):
        if self.handle:
            fcntl.flock(self.handle, fcntl.LOCK_UN)
            self.handle.close()
            logger.info("Lock released")
            try:
                os.remove(self.lock_file)
            except OSError:
                pass
