import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

from dotfilesforge import logger
from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.package_manager import get_package_manager

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

EIM_BASE_URL = "https://dl.espressif.com/dl/eim"
EIM_PACMAN_KEY_FINGERPRINT = "06E9A6C0325E124198C685F18B1F38BDC9383E1D"
EIM_PACMAN_REPO = f"""
[eim]
SigLevel = Required DatabaseOptional TrustAll
Server = {EIM_BASE_URL}/pacman/$arch
"""

PACMAN_CONF = Path("/etc/pacman.conf")
PACMAN_EIM_DB = Path("/var/lib/pacman/sync/eim.db")
APT_KEYRING = Path("/etc/apt/keyrings/eim.gpg")
APT_SOURCES = Path("/etc/apt/sources.list.d/espressif.sources")
APT_LEGACY_LIST = Path("/etc/apt/sources.list.d/espressif.list")
APT_LISTS_DIR = Path("/var/lib/apt/lists")


class EspIdfInstaller:
    def __new__(cls) -> ToolInstaller:

        config = get_config()
        tool_config = config.tools.get("esp_idf")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("Eim", "default"):
            return EspIdfEimInstaller(config)
        else:
            raise ValueError(f"Unknown install method: {method}")


class EspIdfEimInstaller(ToolInstaller):
    """Package-managed installer for Espressif's ``eim-cli``."""

    PACKAGE: str = "eim-cli"

    @property
    @override
    def tool_name(self) -> str:
        return "esp_idf"

    @override
    def get_dependencies(self) -> list[str]:
        manager = get_package_manager().package_manager
        if manager in ("pacman", "yay"):
            if not re.search(r"^\[eim\]\s*$", PACMAN_CONF.read_text(), re.MULTILINE):
                logger.info("Adding the Espressif pacman repository...")
                # The key must be trusted *before* the first database sync.
                key = self._download(f"{EIM_BASE_URL}/eim.asc")
                self._run(["pacman-key", "--add", "-"], stdin_data=key)
                self._run(["pacman-key", "--lsign-key", EIM_PACMAN_KEY_FINGERPRINT])
                self._run(
                    ["tee", "-a", str(PACMAN_CONF)],
                    stdin_data=EIM_PACMAN_REPO.encode(),
                    quiet=True,
                )

            # The central install runs `pacman -S --needed` without -y, so the
            # new repo's database has to be synced here. Full upgrade, never a
            # bare -Sy (partial upgrades are unsupported on Arch). Checking for
            # the db file also recovers from an interrupted earlier run.
            if not PACMAN_EIM_DB.exists():
                logger.info("Syncing package databases for the eim repository...")
                self._run(["pacman", "-Syu", "--noconfirm"])
        elif manager == "apt":
            if not (APT_SOURCES.exists() or APT_LEGACY_LIST.exists()):
                logger.info("Adding the Espressif APT repository...")
                self._run(["install", "-m", "0755", "-d", str(APT_KEYRING.parent)])
                self._write_root_file(
                    APT_KEYRING, self._download(f"{EIM_BASE_URL}/eim.gpg")
                )
                self._write_root_file(
                    APT_SOURCES, self._download(f"{EIM_BASE_URL}/eim.sources")
                )

            # If no package lists from Espressif's host exist yet, fetch them.
            # (Worst case this runs `apt update` once too often; it's harmless.)
            if not any(APT_LISTS_DIR.glob("dl.espressif.com*")):
                logger.info("Updating APT package lists for the eim repository...")
                self._run(["apt", "update"])
        else:
            raise NotImplementedError(f"Unsupported package manager: {manager}")
        return [self.PACKAGE]

    @override
    def get_current_version(self) -> str | None:
        return None

    @override
    def get_latest_version(self) -> str:
        return ""

    @override
    def install(self, version: str) -> None:
        pass

    @override
    def update(self, version: str) -> None:
        pass

    def _write_root_file(self, path: Path, data: bytes, mode: str = "0644") -> None:
        self._run(["tee", str(path)], stdin_data=data, quiet=True)
        self._run(["chmod", mode, str(path)])

    @staticmethod
    def _download(url: str) -> bytes:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content

    @staticmethod
    def _run(
        cmd: list[str],
        *,
        stdin_data: bytes | None = None,
        quiet: bool = False,
    ) -> None:
        """Run a command as root (via sudo unless already root)."""
        if os.geteuid() != 0:
            if shutil.which("sudo") is None:
                raise RuntimeError(
                    f"Root privileges required for {cmd[0]!r}, but sudo was not found"
                )
            cmd = ["sudo", *cmd]

        _ = subprocess.run(
            cmd,
            input=stdin_data,
            check=True,
            stdout=subprocess.DEVNULL if quiet else None,
        )
