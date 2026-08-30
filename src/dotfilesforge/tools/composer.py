import shutil
import subprocess
import sys
from pathlib import Path

import requests

from dotfilesforge import logger
from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class ComposerInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        php_enabled = config.packages.get("php", False)

        if php_enabled == True:
            return ComposerBinaryInstaller()
        else:
            raise ValueError("Unknown config value in 'packages.php'")


class ComposerBinaryInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "composer"

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("composer"):
            return None
        result = subprocess.check_output(
            ["composer", "--version"], text=True, stderr=subprocess.DEVNULL
        )
        return result.splitlines()[-1].split()[2]

    @override
    def get_dependencies(self) -> list[str]:
        return ["php"]

    @override
    def get_latest_version(self) -> str:
        # TODO: Find out how to get latest Version (Github even possible?)

        response = requests.get(
            "https://api.github.com/repos/composer/composer/releases/latest"
        )
        response.raise_for_status()
        return response.json()["tag_name"]

    @override
    def install(self, version: str) -> None:
        download_path = Path().home() / "Downloads"
        install_path = Path().home() / ".local" / "bin"
        _ = subprocess.check_call(
            [
                "php",
                "-r",
                "copy('https://getcomposer.org/installer', 'composer-setup.php');",
            ],
            cwd=download_path,
        )

        # TODO: only valid for this version? what if next version is released
        _ = subprocess.check_call(
            [
                "php",
                "-r",
                "if (hash_file('sha384', 'composer-setup.php') === 'c8b085408188070d5f52bcfe4ecfbee5f727afa458b2573b8eaaf77b3419b0bf2768dc67c86944da1544f06fa544fd47') { echo 'Installer verified'.PHP_EOL; } else { echo 'Installer corrupt'.PHP_EOL; unlink('composer-setup.php'); exit(1); }",
            ],
            cwd=download_path,
        )
        _ = subprocess.check_call(
            [
                "php",
                "composer-setup.php",
                f"--install-dir={install_path}",
                "--filename=composer",
            ],
            cwd=download_path,
        )
        _ = subprocess.check_call(
            [
                "php",
                "-r",
                "unlink('composer-setup.php');",
            ],
            cwd=download_path,
        )
        logger.info(f"Composer '{version}' installed successfully")

    @override
    def update(self, version: str) -> None:
        _ = subprocess.check_call(["composer", "self-update"])

        logger.info(f"Composer updated to '{version}' successfully")
