import collections
from logging import CRITICAL
from logging.handlers import BufferingHandler
from smtplib import SMTP, SMTPException
import sys


META = CRITICAL + 10


class BufferingSMTPHandler(BufferingHandler):

    _SUBSTITUTE_WORDS = ["SUCCEEDED", "FAILED", "SKIPPED", "TOTAL", "RUNTIME", "STATUS"]

    def __init__(self, capacity, mailhost, fromaddr, toaddrs, subject):
        super().__init__(capacity)
        self.mailhost = mailhost
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs
        self.subject = subject
        self.extra = {}

    def emit(self, record):
        """
        Emit a record.

        Append the record. If shouldFlush() tells us to, call flush() to process
        the buffer.
        """
        if not record.msg and isinstance(record.args, collections.abc.Mapping):
            self.extra.update(
                {
                    k: str(v)
                    for k, v in record.args.items()
                    if k in self._SUBSTITUTE_WORDS
                }
            )
            return

        self.buffer.append(record)
        if self.shouldFlush(record):
            self.flush()

    def getSubject(self):
        subject = self.subject
        for sw in self._SUBSTITUTE_WORDS:
            subject = subject.replace("$" + sw, self.extra.get(sw, "<undefined>"))
        return subject

    def flush(self):
        if not self.buffer:
            return
        msg = "From: {}\r\nTo: {}\r\nSubject: {}\r\n\r\n".format(
            self.fromaddr, ",".join(self.toaddrs), self.getSubject(),
        )
        for record in self.buffer:
            msg += self.format(record) + "\r\n"
        msg = msg.encode()

        try:
            with SMTP(*self.mailhost) as smtp:
                smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            self.buffer = []
        except SMTPException as e:
            print("SMTPException: {}".format(e), file=sys.stderr)
            self.handleError(None)
        except Exception as e:
            print("Unknown Exception when sending email: {}".format(e), file=sys.stderr)
            self.handleError(None)
