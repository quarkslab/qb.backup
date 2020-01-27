import logging
from pathlib import Path
import yaml

from . import IncludeLoader


log = logging.getLogger("qb.backup")


class ConfigError(ValueError):
    pass


class Config:

    CONF_LOGGING = Path(__file__).with_name("default.yml").read_text()

    class MetaHost(type):
        def __new__(_, lock=None, port=22):
            class Host:
                _lock = lock
                _port = port

                def __init__(self, hostname, port=None, lock=None):
                    self.hostname = hostname
                    try:
                        self.lock = (
                            Path(lock)
                            if lock
                            else Path(self._lock.format(self.hostname))
                        )
                    except AttributeError:
                        log.error(
                            "Either %s lock or default lock MUST be provided",
                            self.hostname,
                        )
                    self.port = str(port or self._port)

            return Host

    @classmethod
    def load(cls, path):
        """ Load a configuration from a config.yml file.

        :param path: file to read from

        :returns: the configuration read from the file
        :raises: OSError if cannot read path
        :raises: ConfigError if badly formatted configuration file

        """
        try:
            with open(path, "r") as fd:
                log.info("Successfully read configuration from %s", path)
                return Config(yaml.load(fd, Loader=IncludeLoader))
        except yaml.YAMLError as e:
            raise ConfigError(e)

    def __init__(self, conf: dict = {}):
        self._init_logging(conf)
        if "logging" not in conf:
            log.warning("No logging configuration given, default is applied")

        self._init_hosts(conf)

    def _init_logging(self, conf: dict = {}):
        conf = conf.get("logging", {})
        self.logging = yaml.safe_load(self.CONF_LOGGING)
        try:
            self.logging["handlers"]["logs"]["filename"] = conf["filename"]
        except KeyError:
            # conf["filename"] does not exist
            pass
        try:
            subject_error = conf["mail"].pop("subject_error", None)
            subject_status = conf["mail"].pop("subject_status", None)
            self.logging["handlers"]["mail_error"].update(conf["mail"])
            if subject_error:
                self.logging["handlers"]["mail_error"]["subject"] = subject_error
            self.logging["handlers"]["mail_status"].update(conf["mail"])
            if subject_status:
                self.logging["handlers"]["mail_status"]["subject"] = subject_status
        except KeyError:
            # conf["mail"] does not exist, deactivate mails
            self.logging["loggers"]["qb.backup"]["handlers"].remove("mail_error")
            del self.logging["handlers"]["mail_error"]
            self.logging["loggers"]["qb.backup.progress"]["handlers"].remove(
                "mail_status"
            )
            del self.logging["handlers"]["mail_status"]

    def _init_hosts(self, conf: dict = {}):
        self.Host = Config.MetaHost(**conf.get("default", {}))

        self.hosts = [
            self.Host(host) if isinstance(host, str) else self.Host(**host)
            for host in conf.get("hosts", [])
        ]
