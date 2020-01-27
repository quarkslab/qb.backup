#!/usr/bin/python3


import argparse
import logging
import logging.config
from pathlib import Path
import sys

from qb.backup import Backuper, Config, ConfigError


log = logging.getLogger("qb.backup")

_description = """
qb.backup server executable
"""

_epilog = """
exit status:
 0  OK
 1  failure during backups
 2  invalid command line

"""


def run(args):
    try:
        config = Config.load(args.conf)
    except OSError as e:
        # Logging is not configured yet, cannot use it
        print(f"cannot read {args.conf}: {e}", file=sys.stderr)
        exit(1)
    except ConfigError as e:
        # Logging is not configured yet, cannot use it
        print(f"badly formatted file {args.conf}: {e}", file=sys.stderr)
        exit(1)

    # NOTE: this line may raise an uncaught ValueError if there is an issue
    # with the config. To debug efficiently the issue we need the whole
    # exception stack, for example it can be:
    #   ValueError: Unable to configure handler 'logs'
    #   PermissionError: [Errno 13] Permission denied: '/var/log/backup.log'
    logging.config.dictConfig(config.logging)

    if args.exclude:
        # Avoid typos and prevent unintended behavior
        for x in args.exclude:
            if not any(h.hostname == x for h in config.hosts):
                log.error("%r not present in config, aborting.", x)
                exit(1)
        config.hosts = [h for h in config.hosts if h.hostname not in args.exclude]
    if args.only:
        # Avoid typos and prevent unintended behavior
        for o in args.only:
            if all(h.hostname != o for h in config.hosts):
                log.error("%r not present in config, aborting.", o)
                exit(1)
        config.hosts = [h for h in config.hosts if h.hostname in args.only]

    try:
        proc = Backuper(config.hosts, failfast=args.failfast)
        rc = proc.run()
        return rc
    except Exception as e:
        log.exception(e)
        exit(1)


def cli():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=_description,
        epilog=_epilog,
    )
    # NOTE: `dest=` is theoretically unnecessary but as long as
    # https://bugs.python.org/issue29298 is open we need it to prevent a failure when
    # parsing argv=[]
    subcommands = parser.add_subparsers(dest="cmd")
    # NOTE: in python >3.6 you can add `required=True` as a parameter of .add_subparsers
    subcommands.required = True

    run_p = subcommands.add_parser(
        "run",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Run a series of backups according to a conf file",
    )
    run_p.add_argument(
        "-c",
        "--conf",
        metavar="FILENAME",
        type=Path,
        default="/etc/backup/config.yml",
        help="set configuration file",
    )
    limits_p = run_p.add_mutually_exclusive_group()
    limits_p.add_argument(
        "--only", metavar="HOST", nargs="+", help="limit backups to these hosts only"
    )
    limits_p.add_argument(
        "--exclude", metavar="HOST", nargs="+", help="do not backup these hosts"
    )
    run_p.add_argument(
        "-f", "--failfast", action="store_true", help="quit on the first error",
    )
    run_p.set_defaults(func=run)

    return parser


if __name__ == "__main__":  # pragma: no cover
    parser = cli()
    args = parser.parse_args()
    rc = args.func(args)
    exit(rc)
