import unittest
from unittest.mock import Mock, patch

import collections
import logging
from pathlib import Path
from subprocess import CompletedProcess, CalledProcessError, TimeoutExpired

import qb.backup.backup as module


class Host:
    def __init__(self, hostname, port=None, lock=None):
        self.hostname = hostname
        self.port = str(port or 22)
        self.lock = lock or Path("/tmp/qb.backup-test.lock")


class TestFunctions(unittest.TestCase):
    def test_bound_no_title(self):
        text = "This book is largely concerned with Hobbits, and ..."

        res = module.bound(text)
        first, *_, last = res.splitlines()

        self.assertEqual(first, ">" * 40)
        self.assertEqual(last, "<" * 40)
        self.assertIn(text, res)

    def test_bound_with_title(self):
        text = "This book is largely concerned with Hobbits, and ..."
        title = "Concerning Hobbits"

        res = module.bound(text, title)
        first, *_, last = res.splitlines()

        self.assertIn(title, first)
        self.assertIn(title, last)
        self.assertIn(text, res)


def log(msg, *args):
    """ Mockup for logging.Logger.info and so on.
    """
    if len(args) == 1 and isinstance(args[0], collections.abc.Mapping):
        args = args[0]
    # Tries to print the message to be sure substitution is valid
    print(msg % args)


class TestBackuper(unittest.TestCase):
    def setUp(self):
        self.b = module.Backuper([])

        self._log = patch.object(module, "log", spec=logging.Logger)
        self.log = self._log.start()
        self.log.debug.side_effect = log
        self.log.info.side_effect = log
        self.log.warning.side_effect = log
        self.log.error.side_effect = log

        self._log_progress = patch.object(module, "log_progress", spec=logging.Logger)
        self.log_progress = self._log_progress.start()
        self.log_progress.debug.side_effect = log
        self.log_progress.info.side_effect = log
        self.log_progress.warning.side_effect = log
        self.log_progress.error.side_effect = log

    def tearDown(self):
        self._log.stop()

    def test_run(self):
        # fmt: off
        self.b.hosts = [
            Host("foo.test", 22),
            Host("bar.test", 33),
        ]
        # fmt: on
        self.b.backup = Mock()

        self.b.run()

        self.assertEqual(self.b.backup.call_count, 2)

    @patch.object(module.subprocess, "run")
    @patch.object(module, "FLock")
    def test_run_fail_lock(self, m_FLock, m_run):
        host = "example.test"
        m_FLock.side_effect = module.FLockError

        self.b.hosts = [Host(host)]
        rc = self.b.run()

        self.assertEqual(rc, 1)
        self.log.warning.assert_called()
        self.log.error.assert_not_called()
        m_run.assert_not_called()

    @patch.object(module.subprocess, "run")
    def test_run_timeout(self, m_run):
        host = "example.test"
        m_run.side_effect = TimeoutExpired("cmd", 300, "output text", "error text")

        self.b.hosts = [Host(host)]
        rc = self.b.run()

        self.assertEqual(rc, 1)
        self.assertIn(host, " ".join(m_run.call_args[0][0]))
        m_run.assert_called_once()
        self.log.error.assert_called()

    @patch.object(module.subprocess, "run")
    def test_run_failure(self, m_run):
        host = "example.test"
        m_run.side_effect = CalledProcessError(1, "cmd", "output text", "error text")

        self.b.hosts = [Host(host)]
        rc = self.b.run()

        self.assertEqual(rc, 1)
        self.assertIn(host, " ".join(m_run.call_args[0][0]))
        self.log.error.assert_called()

    @patch.object(module.subprocess, "run")
    def test_run_fastfailure(self, m_run):
        host = "example.test"
        m_run.side_effect = (
            CompletedProcess("cmd", 0, "output text"),
            CalledProcessError(1, "cmd", "output text", "error text"),
            CompletedProcess("cmd", 0, "output text"),
        )

        self.b.hosts = [Host(host), Host(host), Host(host)]
        self.b.failfast = True
        rc = self.b.run()

        self.assertEqual(rc, 1)
        self.assertEqual(m_run.call_count, 2)
        self.assertIn(host, " ".join(m_run.call_args[0][0]))
        self.log.error.assert_called()

    @patch.object(module.subprocess, "run")
    def test_run_slowfailure(self, m_run):
        host = "example.test"
        m_run.side_effect = (
            CompletedProcess("cmd", 0, "output text"),
            CalledProcessError(1, "cmd", "output text", "error text"),
            CompletedProcess("cmd", 0, "output text"),
        )

        self.b.hosts = [Host(host), Host(host), Host(host)]
        rc = self.b.run()

        self.assertEqual(rc, 1)
        self.assertEqual(m_run.call_count, 3)
        self.assertIn(host, " ".join(m_run.call_args[0][0]))
        self.log.error.assert_called()

    @patch.object(module.subprocess, "run")
    def test_run_success(self, m_run):
        host = "example.test"
        m_run.return_value = CompletedProcess("cmd", 0, "output text")

        self.b.hosts = [Host(host), Host(host), Host(host)]
        rc = self.b.run()

        self.assertEqual(rc, 0)
        self.assertIn(host, " ".join(m_run.call_args[0][0]))
        self.log.error.assert_not_called()
