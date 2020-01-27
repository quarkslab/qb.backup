from datetime import datetime, timedelta, timezone
import fcntl
from pathlib import Path


class FLockError(OSError):
    pass


class FLock:
    """
    Create an interprocess lock with the flock Unix API.

    >>> with FLock("/path/to/file.lock"):
    ...     ... # Locked code

    WARNING: this lock is not thread-safe and should not be used in a
    multi-threaded environment.

    NOTE: For a better understanding of problematics with locks, check out
    http://0pointer.de/blog/projects/locking.html
    """

    def __init__(self, path, blocking=False):
        # Convert strings if needed
        self.path = Path(path) if isinstance(path, str) else path
        self.flags = fcntl.LOCK_EX
        if not blocking:
            self.flags |= fcntl.LOCK_NB

        self.fd = None

    def acquire(self):
        try:
            self.fd = self.path.open("w")
            fcntl.lockf(self.fd, self.flags)
        except OSError as e:
            self.release()
            raise FLockError(e)

    def release(self):
        if self.fd:
            self.fd.close()
            self.fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


class Timer:
    def __init__(self):
        self._start = None
        self._stop = None

    def start(self):
        self._start = datetime.now(tz=timezone.utc)
        return self._start

    def stop(self):
        self._stop = datetime.now(tz=timezone.utc)
        return self._stop

    @property
    def dt(self):
        if self._start is None or self._stop is None:
            return None
        return self._stop - self._start

    def in_seconds(self):
        dt = self.dt
        if dt is None:
            return None
        secs = dt // timedelta(seconds=1)
        return timedelta(seconds=secs)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
