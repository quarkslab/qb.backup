from setuptools import setup


setup(
    name="qb-backup",
    version="0.1.0",
    author="Quarkslab",
    description=(
        "The server-side script of the qb.backup orchestration solution."
    ),
    packages=(
        "qb.backup",
    ),
    package_dir={
        "qb.backup": "lib",
    },
    namespace_packages=(
        "qb",
    ),
    install_requires=(
        "pyyaml"
    ),
)
