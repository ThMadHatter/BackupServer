import pytest
from pathlib import Path
from backup_server.locking import Lock
import os

def test_lock_acquire_release(tmp_path):
    lock_file = tmp_path / "test.lock"
    lock = Lock(lock_file)

    lock.acquire()
    assert lock_file.exists()

    lock.release()
    assert not lock_file.exists()

def test_lock_context_manager(tmp_path):
    lock_file = tmp_path / "test.lock"

    with Lock(lock_file):
        assert lock_file.exists()

    assert not lock_file.exists()

def test_lock_concurrent_fail(tmp_path):
    lock_file = tmp_path / "test.lock"
    lock1 = Lock(lock_file)
    lock2 = Lock(lock_file)

    lock1.acquire()
    with pytest.raises(RuntimeError):
        lock2.acquire()

    lock1.release()
