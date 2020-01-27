import unittest
from unittest.mock import mock_open, patch

from pathlib import Path

import qb.backup.config.config as module


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._log = patch.object(module, "log")
        self.log = self._log.start()

    def tearDown(self):
        self._log.stop()

    def test_load(self):
        with patch("builtins.open", mock_open(read_data="{}")) as m_open:
            # XXX: required for tests to pass in python <3.8
            m_open.return_value.name = "whatever"
            res = module.Config.load(Path("/path/to/foo"))

        m_open.assert_called_once_with(Path("/path/to/foo"), "r")
        self.assertIsInstance(res, module.Config)

    def test_load_configerror(self):
        with self.assertRaises(module.ConfigError):
            with patch("builtins.open", mock_open(read_data="{")) as m_open:
                # XXX: required for tests to pass in python <3.8
                m_open.return_value.name = "whatever"
                module.Config.load(Path("/path/to/foo"))

        m_open.assert_called_once_with(Path("/path/to/foo"), "r")

    @patch("builtins.open")
    def test_load_oserror(self, m_open):
        m_open.side_effect = OSError

        with self.assertRaises(OSError):
            module.Config.load(Path("/path/to/foo"))

        m_open.assert_called_once_with(Path("/path/to/foo"), "r")

    def test___init__hosts(self):
        dct = {
            "default": {"port": 33},
            "hosts": ["foo.test", {"hostname": "bar.test", "port": 44}],
            "logging": {},
        }

        foo, bar = module.Config(dct).hosts

        self.assertEqual(foo.hostname, "foo.test")
        self.assertEqual(foo.port, "33")
        self.assertEqual(bar.hostname, "bar.test")
        self.assertEqual(bar.port, "44")

    def test___init__logging0(self):
        dct = {
            "logging": {
                "filename": "/path/to/foo.log",
                "mail": {
                    "subject_error": "This is the error subject",
                    "fromaddr": "bar@backup.test",
                },
            }
        }

        logging = module.Config(dct).logging

        self.assertEqual(logging["handlers"]["logs"]["filename"], "/path/to/foo.log")
        self.assertEqual(
            logging["handlers"]["mail_error"]["fromaddr"], "bar@backup.test"
        )
        self.assertEqual(
            logging["handlers"]["mail_status"]["fromaddr"], "bar@backup.test"
        )
        self.assertEqual(
            logging["handlers"]["mail_error"]["subject"], "This is the error subject"
        )
        self.assertEqual(logging["handlers"]["mail_status"]["subject"], "Backup status")
        self.assertNotIn("subject_error", logging["handlers"]["mail_error"])
        self.assertNotIn("subject_error", logging["handlers"]["mail_status"])

    def test___init__logging1(self):
        dct = {
            "logging": {
                "mail": {
                    "subject_error": "This is the error subject",
                    "subject_status": "This is the status subject",
                }
            }
        }

        logging = module.Config(dct).logging

        self.assertEqual(logging["handlers"]["logs"]["filename"], "./backup.log")
        self.assertNotIn("fromaddr", logging["handlers"]["mail_error"])
        self.assertNotIn("fromaddr", logging["handlers"]["mail_status"])
        self.assertNotIn("toaddrs", logging["handlers"]["mail_error"])
        self.assertNotIn("toaddrs", logging["handlers"]["mail_status"])
        self.assertNotIn("mailhost", logging["handlers"]["mail_error"])
        self.assertNotIn("mailhost", logging["handlers"]["mail_status"])
        self.assertEqual(
            logging["handlers"]["mail_error"]["subject"], "This is the error subject"
        )
        self.assertEqual(
            logging["handlers"]["mail_status"]["subject"], "This is the status subject"
        )
        self.assertNotIn("subject_error", logging["handlers"]["mail_error"])
        self.assertNotIn("subject_error", logging["handlers"]["mail_status"])
        self.assertNotIn("subject_status", logging["handlers"]["mail_error"])
        self.assertNotIn("subject_status", logging["handlers"]["mail_status"])
