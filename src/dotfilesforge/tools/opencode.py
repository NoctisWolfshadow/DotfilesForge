import os
import shutil
import subprocess
import sys

import requests

from dotfilesforge import logger
from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class OpencodeInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("opencode")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("bin", "default"):
            return OpencodeBinaryInstaller()
        else:
            raise ValueError(f"Unknown install method: {method}")


class OpencodeBinaryInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "opencode"

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("opencode"):
            return None
        result = subprocess.check_output(["opencode", "--version"], text=True)
        return result.splitlines()[0].split()[-1]

    @override
    def get_dependencies(self) -> list[str]:
        return ["curl"]

    @override
    def get_latest_version(self) -> str:
        """Get latest binary release version from GitHub"""
        response = requests.get(
            "https://api.github.com/repos/anomalyco/opencode/releases/latest"
        )
        response.raise_for_status()
        return response.json()["tag_name"]

    @override
    def install(self, version: str) -> None:
        _ = subprocess.check_call(
            ["curl", "-fsSL", "https://opencode.ai/install", "|", "bash"],
            env=os.environ.copy(),
            shell=True,
        )

        logger.info(f"Opencode {version} installed successfully")

    @override
    def update(self, version: str) -> None:
        _ = subprocess.check_call(["opencode", "upgrade"])

        logger.info(f"Opencode updated to '{version}' successfully")
