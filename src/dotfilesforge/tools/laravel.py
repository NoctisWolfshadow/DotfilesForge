import shutil
import subprocess
import sys

import requests

from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.tools.composer import ComposerInstaller

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class LaravelInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("yazi")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("composer", "default"):
            return LaravelComposerInstaller()
        else:
            raise ValueError("Unknown config value in 'Tool.laravel'")


class LaravelComposerInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "laravel"

    @override
    def get_dependencies(self) -> list[str]:
        return []

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("laravel"):
            return None
        result = subprocess.check_output(["laravel", "-v"], text=True)
        return result.splitlines()[0].split()[-1]

    @override
    def get_latest_version(self) -> str:
        return self.get_latest_version_from_packagist()

    @override
    def install(self, version: str):
        if not shutil.which("composer"):
            composer = ComposerInstaller()
            composer.check_and_install()

        _ = subprocess.check_call(
            ["composer", "global", "install", "laravel/installer"]
        )

    @override
    def update(self, version: str):
        _ = subprocess.check_call(["composer", "global", "update", "laravel/installer"])

    def get_latest_version_from_packagist(self) -> str:
        url = "https://repo.packagist.org/p2/laravel/installer.json"
        latest_version: str = requests.get(url).json()["packages"]["laravel/installer"][
            0
        ]["version"]
        latest_version = latest_version.lstrip("v")

        if not latest_version:
            raise ValueError("No latest version found")

        return latest_version
