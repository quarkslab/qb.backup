import unittest
from unittest.mock import Mock, patch, ANY
from parameterized import parameterized

import logging
import qb.backup.logging as module
import smtplib


class TestBufferingSMTPHandler(unittest.TestCase):
    def setUp(self):
        self.h = module.BufferingSMTPHandler(
            4096, ("mail.test", 25), "from@qb", ["to@qb"], "subject"
        )
        self.h.format = Mock(return_value="<o/")

    def tearDown(self):
        pass

    @parameterized.expand([(True,), (False,)])
    def test_emit_regular(self, flush):
        self.h.shouldFlush = Mock(return_value=flush)
        self.h.flush = Mock()
        orig_extra = self.h.extra.copy()
        record = logging.makeLogRecord({"msg": "my log message", "args": {"TOTAL": 25}})

        self.h.emit(record)

        self.assertEqual(orig_extra, self.h.extra)
        if flush:
            self.h.flush.assert_called_once()
        else:
            self.h.flush.assert_not_called()

    def test_emit_update(self):
        assert "SKIPPED" in self.h._SUBSTITUTE_WORDS
        assert "TOTAL" in self.h._SUBSTITUTE_WORDS
        assert "FOO" not in self.h._SUBSTITUTE_WORDS

        record = logging.makeLogRecord(
            {"msg": "", "args": {"SKIPPED": 3, "TOTAL": 13, "FOO": 6}}
        )

        self.h.emit(record)

        self.assertEqual(self.h.extra["SKIPPED"], "3")
        self.assertEqual(self.h.extra["TOTAL"], "13")
        self.assertNotIn("FOO", self.h.extra)

    @patch.object(module, "SMTP")
    def test_flush_empty(self, m_SMTP):
        self.h.buffer = []

        self.h.flush()

        m_SMTP.assert_not_called()

    @patch.object(module, "SMTP")
    def test_flush_fail_connect(self, m_SMTP):
        self.h.buffer = [Mock()]
        self.h.format.return_value = "This is a mail"

        m_SMTP.side_effect = module.SMTPException

        self.h.flush()
        # Cannot check that print is called, because everybody calls it

    @patch.object(module, "SMTP")
    def test_flush_fail_unknown(self, m_SMTP):
        self.h.buffer = [Mock()]
        self.h.format.return_value = "This is a mail"

        m_SMTP.side_effect = Exception

        self.h.flush()
        # Cannot check that print is called, because everybody calls it

    @patch.object(module, "SMTP")
    def test_flush_success(self, m_SMTP):
        self.h.buffer = [Mock()]
        self.h.format.return_value = "This is a mail"

        smtp = m_SMTP.return_value.__enter__.return_value = Mock(smtplib.SMTP)

        self.h.flush()

        smtp.sendmail.assert_called_once_with("from@qb", ["to@qb"], ANY)
        msg = smtp.sendmail.call_args[0][2]
        self.assertIn(b"This is a mail", msg)

    @patch.object(module, "SMTP")
    def test_flush_substitute(self, m_SMTP):
        self.h.subject = "Success $SUCCEEDED / $TOTAL"
        self.h.extra = {"TOTAL": "13", "SKIPPED": "4"}
        self.h.buffer = [Mock()]
        self.h.format.return_value = "This is a mail"

        smtp = m_SMTP.return_value.__enter__.return_value = Mock(smtplib.SMTP)

        self.h.flush()

        smtp.sendmail.assert_called_once_with("from@qb", ["to@qb"], ANY)
        msg = smtp.sendmail.call_args[0][2]
        self.assertIn(b"Subject: Success <undefined> / 13", msg)

    @patch.object(module, "SMTP")
    def test_update(self, m_SMTP):
        assert "TOTAL" in self.h._SUBSTITUTE_WORDS

        self.h.setLevel(logging.WARNING)
        self.h.subject = "$TOTAL hosts handled"

        log = logging.getLogger("qb.backup.test")
        log.setLevel(logging.INFO)
        log.addHandler(self.h)

        # Level is not high enough to get to the handler
        log.info("", {"TOTAL": 24})
        subject = self.h.getSubject()
        self.assertIn("<undefined>", subject)

        # Using META level, it works whatever the levels
        log.log(module.META, "", {"TOTAL": 63})
        subject = self.h.getSubject()
        self.assertIn("63", subject)
