from __future__ import annotations

import os
import subprocess
import sys
from abc import ABC, abstractmethod

from dotfilesforge import logger
from dotfilesforge.config import Config, get_config
from dotfilesforge.package_manager import get_package_manager

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

_shell: base_shell | None = None
_shell_checked = False


class Shell:
    def __new__(cls) -> base_shell | None:
        config = get_config()
        shell: str | None = config.settings.shell

        if not shell:
            return None

        if shell == "zsh":
            return ZSH()
        elif shell == "fish":
            return FISH()
        else:
            raise ValueError(f"Unknown Shell: {shell}")


class base_shell(ABC):
    def __init__(self, config: Config | None = None):
        self.config: Config = config or get_config()

    @abstractmethod
    def getPackage(self) -> str: ...

    @abstractmethod
    def getName(self) -> str: ...

    def enable_shell(self):
        shell = self.getCurrentShell()

        if shell != self.getName():
            logger.info(f"Updating Shell from {shell} to {self.getName()}")
            _ = subprocess.check_call(["chsh", "-s", f"$(which {self.getName()})"])

    def getCurrentShell(self) -> str:
        shell_path: str | None = os.environ.get("SHELL")
        if not shell_path:
            raise SystemExit(logger.error("Could not detect Shell."))
        shell_list = shell_path.split("/")
        return shell_list[-1]


class ZSH(base_shell):
    @override
    def getName(self) -> str:
        return "zsh"

    @override
    def getPackage(self) -> str:
        package_manager = get_package_manager().getPackageManager()

        names = {"pacman": "zsh", "yay": "zsh", "apt": "zsh"}
        if not names.get(package_manager, None):
            raise SystemExit(
                logger.error("No available Package found for your PackageManager.")
            )

        return names[package_manager]


class FISH(base_shell):
    @override
    def getName(self) -> str:
        return "fish"

    @override
    def getPackage(self) -> str:
        package_manager = get_package_manager().getPackageManager()

        names = {"pacman": "fish", "yay": "fish", "apt": "fish"}
        if not names.get(package_manager, None):
            raise SystemExit(
                logger.error("No available Package found for your PackageManager.")
            )

        if package_manager == "apt":
            _ = self.add_ppa()

        return names[package_manager]

    def add_ppa(self):
        _ = subprocess.run(["sudo", "apt-add-repository", "ppa:fish-shell/release-4"])


def get_shell() -> base_shell | None:
    global _shell, _shell_checked
    if not _shell_checked:
        _shell = Shell()
        _shell_checked = True

    return _shell
