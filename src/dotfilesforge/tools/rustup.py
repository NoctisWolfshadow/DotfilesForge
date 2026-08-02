import os
import shutil
import subprocess
import sys

import requests

from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class RustupInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("rustup")

        return RustupBinaryInstaller(config)


class RustupBinaryInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "rustup"

    @override
    def get_dependencies(self) -> list[str]:
        return []

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("rustup"):
            return None

        result = subprocess.check_output(
            ["rustup", "-V"], text=True, stderr=subprocess.DEVNULL
        )
        return result.splitlines()[0].split()[1]

    @override
    def get_latest_version(self) -> str:
        response = requests.get("https://api.github.com/repos/rust-lang/rustup/tags")
        response.raise_for_status()
        return response.json()[0]["name"]

    @override
    def install(self, version: str) -> None:
        _ = subprocess.run(
            [
                "curl",
                "--proto",
                "=https",
                "--tlsv1.2",
                "-sSf",
                "https://sh.rustup.rs",
                "|",
                "sh",
            ],
            shell=True,
            env=os.environ.copy(),
        )

    @override
    def update(self, version: str) -> None:
        _ = subprocess.check_call(["rustup", "update"])
