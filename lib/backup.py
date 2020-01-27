import logging
import subprocess

from .logging import META
from ._utils import FLock, FLockError, Timer


log = logging.getLogger("qb.backup")
log_progress = logging.getLogger("qb.backup.progress")


def bound(text, title=""):
    if title:
        title = " " + title + " "
    return ">>>{1:><37}\n{0}\n<<<{1:<<37}".format(text, title)


def handle_SubprocessError(e: subprocess.SubprocessError, hostname="<undefined>"):
    log_progress.error("%-20s: backup failed. More details in another email", hostname)
    log.error("erroneous command: %r", e.cmd)
    log.error(bound(e.stderr, "stderr"))
    log.error(bound(e.stdout, "stdout"))


class Backuper:
    def __init__(self, hosts, failfast=False):
        self.hosts = hosts
        self.failfast = failfast

    def run(self):
        rc = 0
        succeeded = 0
        failed = 0
        with Timer() as timer:
            for host in self.hosts:
                try:
                    self.backup(host)
                    succeeded += 1
                except subprocess.TimeoutExpired as e:
                    log.error("backup of %s timed out (%ds)", host.hostname, e.timeout)
                    handle_SubprocessError(e, host.hostname)
                    failed += 1
                    rc = 1
                except subprocess.CalledProcessError as e:
                    log.error("backup of %s returned %d", host.hostname, e.returncode)
                    handle_SubprocessError(e, host.hostname)
                    failed += 1
                    rc = 1
                except FLockError:
                    log.warning("failed to take lock on file %s", host.lock)
                    log.warning("backup of host %s aborted", host.hostname)
                    failed += 1
                    rc = 1
                if self.failfast and rc != 0:
                    break

        total = len(self.hosts)
        summary = {
            "SUCCEEDED": succeeded,
            "FAILED": failed,
            "SKIPPED": total - succeeded - failed,
            "TOTAL": total,
            "RUNTIME": timer.in_seconds(),
            "STATUS": "success" if rc == 0 else "failure",
        }

        # Add extra info for mail handler
        log_progress.log(META, "", summary)

        log_progress.info("{:<20}: RUNTIME %s".format("Summary"), timer.in_seconds())
        log_progress.info(
            "{:<20}: ".format("Summary")
            + "SUCCESS %(SUCCEEDED)3d/%(TOTAL)-3d  "  # fmt: off
            "FAILURE %(FAILED)3d/%(TOTAL)-3d  "
            "SKIPPED %(SKIPPED)3d/%(TOTAL)-3d",
            summary,
        )
        return rc

    def backup(self, host):
        """ Perform the backup of an host.
        :param host: Host to backup.
        :raises subprocess.TimeoutExpired:
        :raises subprocess.CalledProcessError:
        :raises FLockError:

        """
        log_progress.info("%-20s: starting backup", host.hostname)
        # fmt: off
        cmd = [
            "ssh",
            "-o", "ServerAliveInterval=10",
            "-o", "ServerAliveCountMax=30",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-p", host.port,
            "-R", "64064:localhost:22",
            "-l", "root",
            host.hostname,
        ]
        # fmt: on

        log.debug("run command: %r", cmd)
        with FLock(host.lock):
            p = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=23 * 3600 + 600,  # +10min for checkpoints
                check=True,
                universal_newlines=True,
            )
        log_progress.info("%-20s: backup completed successfully", host.hostname)
        log.info(bound(p.stderr, f"stderr {host.hostname}"))
