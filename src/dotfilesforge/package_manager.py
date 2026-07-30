from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

from dotfilesforge import logger
from dotfilesforge.config import Config, get_config
from dotfilesforge.representation import build_repr

COMMAND_LIST: dict[str, dict[str, list[str]]] = {
    "pacman": {
        "install": ["sudo", "pacman", "-S", "--noconfirm", "--needed"],
        "update": ["sudo", "pacman", "-Syu"],
        "search": ["pacman", "-Ss"],
    },
    "yay": {
        "install": ["yay", "-S", "--noconfirm", "--needed"],
        "update": ["yay", "-Syu"],
        "search": ["yay", "-Ss"],
    },
    "apt": {
        "install": ["sudo", "apt", "install"],
        "update": ["sudo", "apt", "update"],
        "upgrade": ["&&", "sudo", "apt", "upgrade", "-y"],
        "search": ["apt", "search"],
    },
}

BASE_PACKAGES: list[str] = [
    "7zip",
    "ccache",
    "cmake",
    "curl",
    "gcc",
    "gettext",
    "git",
    "stow",
    "unzip",
]

PHP_PACKAGES: dict[str, list[str]] = {
    "pacman": ["php", "php-gd", "php-sqlite", "php-pgsql", "xdebug"],
    "apt": ["php"],
}

_package_manager: PackageManager | None = None


@dataclass
class PackageManager:
    def __init__(self, config: Config | None = None):
        self.package_manager: str = self.getPackageManager()
        self.commands: dict[str, list[str]] = COMMAND_LIST[self.package_manager]
        self.config: Config = config or get_config()

    @override
    def __repr__(self) -> str:
        return build_repr(self)

    def update_packages(self) -> None:
        cmd = self.commands["update"]
        if self.package_manager == "apt":
            cmd += self.commands["upgrade"]
        _ = subprocess.run(cmd)

    def getPackages(self) -> list[str]:
        package_manager = self.package_manager
        packages: list[str] = self.config.packages[self.package_manager]
        if self.config.packages["php"]:
            if package_manager == "apt":
                # TODO: if apt add ppa for php (ondrej/php)
                _ = subprocess.run(
                    ["sudo", package_manager, "add-apt-repository", "ppa:ondrej/php"]
                )
            packages = packages + PHP_PACKAGES[package_manager]
        if package_manager == "yay":
            packages = self.config.packages["pacman"] + packages
        return packages

    def getInstall(self) -> list[str]:
        return self.commands["install"]

    def searchPackage(self) -> list[str]:
        return self.commands["search"]

    def getPackageManager(self) -> str:
        if shutil.which("pacman"):
            if shutil.which("yay"):
                return "yay"
            return "pacman"

        if shutil.which("apt"):
            return "apt"

        raise SystemExit(logger.error("No valid Package Manager found."))

    def install_packages(self, packages: list[str]) -> None:
        # Search packages from Config enabled Installers and add them for Install so this is only called once
        unique_packages = list(set(BASE_PACKAGES + packages))
        # print(unique_packages)
        _ = subprocess.run(self.getInstall() + unique_packages)


def get_package_manager() -> PackageManager:
    global _package_manager
    if _package_manager is None:
        _package_manager = PackageManager()
    return _package_manager
