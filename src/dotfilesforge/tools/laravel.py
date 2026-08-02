import shutil
import subprocess
import sys

from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.tools.composer import ComposerInstaller

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class FzFInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        laravel_enabled = config.packages.get("laravel", False)

        if laravel_enabled:
            return LaravelComposerInstaller()
        else:
            raise ValueError("Unknown config value in 'packages.laravel'")


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
        return None

    @override
    def get_latest_version(self) -> str:
        return ""

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
