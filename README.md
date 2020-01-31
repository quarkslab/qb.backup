# qb.backup

*qb.backup* is a server side script that orchestrates backups of Linux hosts.

This script has been designed to run in a FreeBSD 11.3 jail on a FreeNAS 11.2-U7
server, which comes with Python 3.7. Python 3.7 and above are supported, and
Python 3.6 is supported as best effort.

Backuped hosts must be configured according to the Ansible role
[qb.backup](https://github.com/quarkslab/ansible-role-qb.backup).

This script and the FreeBSD Jail can be setup using the Ansible role
[qb.backup_server](https://github.com/quarkslab/ansible-role-qb.backup_server).

You can see an example playbook implementing those various roles here:
[ansible-playbook-qb.backup](https://github.com/quarkslab/ansible-playbook-qb.backup).

## Getting started

Requirements:
- *python >= 3.6*

```console
$ pip install .
$ python3 main.py run --help
$ python3 main.py run --conf /path/to/config.yml
```

## Tests

```console
$ pip install parameterized coverage black
$ black --check --diff --target-version=py36 lib tests main.py
$ coverage run --source=qb.backup,main -m unittest discover -vb -s tests -t .
$ coverage report -m
```
