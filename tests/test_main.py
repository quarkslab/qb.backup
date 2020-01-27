import unittest
from unittest.mock import Mock, mock_open, patch, sentinel
from parameterized import parameterized

from pathlib import Path
import sys

from qb.backup import ConfigError

import main as module


if sys.version_info < (3, 7):
    from collections import namedtuple as _namedtuple
    import functools

    # In python <3.7 namedtuple does not have the `default` keyword. This code add this
    # feature.
    # Rather than patching directly namedtuple we simply create a function that pre-fill
    # keywords arguments of a lazily instanciated and returned namedtuple
    @functools.wraps(_namedtuple)
    def namedtuple(*args, defaults=None, **kwargs):
        _NamedTuple = _namedtuple(*args, **kwargs)
        if defaults is None:
            return _NamedTuple
        # Eg.
        # _NamedTuple._fields = ('a', 'b', 'c'); defaults = [2, 3]
        # fields_defaults = {'b': 2, 'c': 3}
        field_defaults = dict(
            reversed(list(zip(reversed(_NamedTuple._fields), reversed(defaults))))
        )

        def new(*args, **kwargs):
            # NOTE: Not a deep copy but a simple copy in order to have the same behavior
            # as namedtuple in python >=3.7
            _kwargs = field_defaults.copy()
            _kwargs.update(kwargs)
            return _NamedTuple(*args, **_kwargs)

        return new


else:
    from collections import namedtuple


Args = namedtuple(
    "Args",
    "conf only exclude failfast",
    defaults=["/path/to/config", None, None, False],
)
WhateverException = type("WhateverException", (Exception,), {})


class TestRun(unittest.TestCase):

    CONF_DATA = """{
        "hosts": ["foo.test", {"hostname": "bar.test", "port": 23}],
        "default": {"lock": "/var/lock/backup/{}.lock"}
    }"""

    def setUp(self):
        self.args = Args()
        log_patcher = patch.object(module, "log")
        self.log = log_patcher.start()
        self.addCleanup(log_patcher.stop)

    def tearDown(self):
        pass

    @patch.object(module.Config, "load", Mock(side_effect=OSError))
    def test_config_oserror(self):
        with self.assertRaises(SystemExit) as ctx:
            module.run(self.args)

        self.assertEqual(ctx.exception.args, (1,))

    @patch.object(module.Config, "load", Mock(side_effect=ConfigError))
    def test_config_configerror(self):
        with self.assertRaises(SystemExit) as ctx:
            module.run(self.args)

        self.assertEqual(ctx.exception.args, (1,))

    @patch("builtins.open", mock_open(read_data=CONF_DATA))
    @patch.object(module, "Backuper")
    def test_proc_error(self, m_Backuper):
        # XXX: required for tests to pass in python <3.8
        open.return_value.name = "whatever"
        m_Backuper.return_value.run.side_effect = WhateverException

        with self.assertRaises(SystemExit) as ctx:
            module.run(self.args)

        self.assertEqual(ctx.exception.args, (1,))

    @patch("builtins.open", mock_open(read_data=CONF_DATA))
    @patch.object(module, "Backuper")
    def test_proc(self, m_Backuper):
        # XXX: required for tests to pass in python <3.8
        open.return_value.name = "whatever"
        m_Backuper.return_value.run.return_value = sentinel.rc

        res = module.run(self.args)

        self.assertEqual(res, sentinel.rc)
        self.log.exception.assert_not_called()

        hosts = m_Backuper.call_args[0][0]  # args[0]
        self.assertEqual(hosts[0].hostname, "foo.test")
        self.assertEqual(hosts[0].port, "22")
        self.assertEqual(hosts[1].hostname, "bar.test")
        self.assertEqual(hosts[1].port, "23")

    @patch("builtins.open", mock_open(read_data=CONF_DATA))
    @patch.object(module, "Backuper")
    def test_proc_only(self, m_Backuper):
        # XXX: required for tests to pass in python <3.8
        open.return_value.name = "whatever"
        args = Args(only=["bar.test"])

        module.run(args)

        hosts = m_Backuper.call_args[0][0]  # args[0]
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].hostname, "bar.test")
        self.assertEqual(hosts[0].port, "23")

    @patch("builtins.open", mock_open(read_data=CONF_DATA))
    @patch.object(module, "Backuper")
    def test_proc_only_error(self, m_Backuper):
        # XXX: required for tests to pass in python <3.8
        open.return_value.name = "whatever"
        args = Args(only=["xxx.test"])

        with self.assertRaises(SystemExit) as ctx:
            module.run(args)

        self.assertEqual(ctx.exception.args, (1,))
        self.log.error.assert_called_once()

    @patch("builtins.open", mock_open(read_data=CONF_DATA))
    @patch.object(module, "Backuper")
    def test_proc_exclude(self, m_Backuper):
        # XXX: required for tests to pass in python <3.8
        open.return_value.name = "whatever"
        args = Args(exclude=["foo.test"])

        module.run(args)

        hosts = m_Backuper.call_args[0][0]  # args[0]
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].hostname, "bar.test")
        self.assertEqual(hosts[0].port, "23")

    @patch("builtins.open", mock_open(read_data=CONF_DATA))
    @patch.object(module, "Backuper")
    def test_proc_exclude_error(self, m_Backuper):
        # XXX: required for tests to pass in python <3.8
        open.return_value.name = "whatever"
        args = Args(exclude=["xxx.test"])

        with self.assertRaises(SystemExit) as ctx:
            module.run(args)

        self.assertEqual(ctx.exception.args, (1,))
        self.log.error.assert_called_once()


class TestCli(unittest.TestCase):
    def setUp(self):
        self.parser = module.cli()

    def tearDown(self):
        pass

    # fmt: off
    @parameterized.expand([
        ((),),
        (("badcmd",),),
        (("run", "--badarg"),),
        (("run", "--conf"),),
        (("run", "--only"),),
        (("run", "--exclude"),),
        (("run", "--only", "foo.test", "--exclude", "bar.test"),),
    ])
    # fmt: on
    def test_bad_cl(self, args):
        with self.assertRaises(SystemExit) as ctx:
            self.parser.parse_args(args)

        self.assertEqual(ctx.exception.args, (2,))

    def test_run(self):
        args = ("run", "--conf", "/path/to/foo", "--failfast")

        parsed = self.parser.parse_args(args)

        self.assertEqual(parsed.conf, Path("/path/to/foo"))
        self.assertTrue(parsed.failfast)

    def test_run_default(self):
        args = ("run",)

        parsed = self.parser.parse_args(args)

        self.assertEqual(parsed.conf, Path("/etc/backup/config.yml"))
        self.assertFalse(parsed.failfast)
