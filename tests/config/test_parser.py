import unittest
from unittest.mock import Mock, patch

from io import BytesIO
from pathlib import Path
import yaml

import qb.backup.config.parser as module


class TestIncludeLoader(unittest.TestCase):
    def setUp(self):
        self.loader = module.IncludeLoader(b"whatever")

    @patch.object(module.Path, "glob")
    def test_include_empty(self, m_glob):
        m_glob.return_value = ()

        res = self.loader.include(Mock(yaml.ScalarNode, value="whatever"))

        self.assertEqual(res, [])

    @patch("builtins.open")
    @patch.object(module.Path, "glob")
    def test_include_mappings(self, m_glob, m_open):
        m_glob.return_value = (Mock(Path), Mock(Path))
        m_open.side_effect = (BytesIO(b'{"a": 1}'), BytesIO(b'{"b": 2}'))

        res = self.loader.include(Mock(yaml.ScalarNode, value="/path/to/whatever"))

        self.assertEqual(res, {"a": 1, "b": 2})
        # Path.glob must not be called with an absolute pattern
        self.assertFalse(m_glob.call_args[0][0].startswith("/"))

    @patch("builtins.open")
    @patch.object(module.Path, "glob")
    def test_include_sequences(self, m_glob, m_open):
        m_glob.return_value = (Mock(Path), Mock(Path))
        m_open.side_effect = (BytesIO(b"[1, 2, 3]"), BytesIO(b"[4, 5]"))

        res = self.loader.include(Mock(yaml.ScalarNode, value="./relpath/to/whatever"))

        self.assertEqual(list(res), [1, 2, 3, 4, 5])
        # Path.glob must not be called with an absolute pattern
        self.assertFalse(m_glob.call_args[0][0].startswith("/"))

    def test_merge_empty(self):
        res = module.IncludeLoader.merge(())

        self.assertEqual(res, [])

    def test_merge_mappings(self):
        res = module.IncludeLoader.merge(({"a": 1, "b": 2}, {"c": 3}, {"d": 2}))

        self.assertEqual(res, {"a": 1, "b": 2, "c": 3, "d": 2})

    def test_merge_sequences(self):
        res = module.IncludeLoader.merge(([1, 2, 3], [2], [4, 0]))

        self.assertEqual(list(res), [1, 2, 3, 2, 4, 0])
