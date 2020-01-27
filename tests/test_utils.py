import unittest
from unittest.mock import Mock, patch, ANY

from datetime import timedelta
from pathlib import Path
import time

import qb.backup._utils as module


class TestFLock(unittest.TestCase):
    def setUp(self):
        self._lockf = patch.object(module.fcntl, "lockf")
        self.lockf = self._lockf.start()

    def tearDown(self):
        self._lockf.stop()

    def test_lock_successful(self):
        lockfile = Mock(Path)
        fd = lockfile.open.return_value

        with module.FLock(lockfile):
            self.lockf.assert_called_once_with(fd, ANY)
            fd.close.assert_not_called()
        fd.close.assert_called_once_with()

    def test_lock_fail_nonblocking(self):
        lockfile = Mock(Path)
        fd = lockfile.open.return_value
        self.lockf.side_effect = OSError

        with self.assertRaises(module.FLockError):
            with module.FLock(lockfile):
                pass
        self.lockf.assert_called_once_with(fd, ANY)
        fd.close.assert_called_once_with()

    def test_lock_fail_blocking(self):
        lockfile = Mock(Path)
        fd = lockfile.open.return_value
        self.lockf.side_effect = lambda *x: time.sleep(0.2)

        with module.FLock(lockfile):
            pass
        self.lockf.assert_called_once_with(fd, ANY)
        fd.close.assert_called_once_with()

    @patch.object(module, "Path")
    def test_lock_string_successful(self, m_Path):
        """ FLock works with string path as well
        """
        m_Path.return_value = lockfile = Mock(Path)
        fd = lockfile.open.return_value

        with module.FLock("lockfile.lock"):
            self.lockf.assert_called_once_with(fd, ANY)
            fd.close.assert_not_called()
        m_Path.assert_called_once_with("lockfile.lock")
        fd.close.assert_called_once_with()


class TestTimer(unittest.TestCase):
    def test_timer_context(self):
        with module.Timer() as timer:
            time.sleep(0.2)
        seconds = timer.dt.total_seconds()

        self.assertLess(0.1, seconds)
        self.assertLess(seconds, 0.3)

    def test_timer_manual(self):
        timer = module.Timer()

        timer.start()
        time.sleep(0.1)
        timer.stop()
        seconds = timer.dt.total_seconds()

        self.assertLess(0.05, seconds)
        self.assertLess(seconds, 0.15)

    def test_timer_unused(self):
        timer = module.Timer()
        self.assertIsNone(timer.dt)
        self.assertIsNone(timer.in_seconds())

        timer.start()
        self.assertIsNone(timer.dt)
        self.assertIsNone(timer.in_seconds())

        timer.stop()
        self.assertIsNotNone(timer.dt)
        self.assertIsNotNone(timer.in_seconds())

    def test_in_seconds(self):
        timer = module.Timer()
        start = timer.start()
        timer._stop = start + timedelta(seconds=12345.6789)

        secs = timer.in_seconds()
        self.assertEqual(secs, timedelta(seconds=12345))
        # No decimal part in the string repr
        self.assertNotIn(".", str(secs))
