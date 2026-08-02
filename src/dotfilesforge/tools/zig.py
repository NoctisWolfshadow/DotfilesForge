import shutil
import subprocess
import sys
from functools import cached_property
from pathlib import Path

import requests
from packaging.version import Version

from dotfilesforge import logger
from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class ZigInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("ghostty")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("bin", "default"):
            return ZigBinaryInstaller(config)
        else:
            raise ValueError(f"Unknown install method: {method}")


class ZigBinaryInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        if self.ghostty:
            return "zig-ghostty"
        return "zig"

    @cached_property
    def install_path(self) -> Path:
        return Path(self.config.paths.git_repos) / self.tool_name

    @override
    def get_current_version(self) -> str | None:
        path = self.install_path / "zig"
        if not shutil.which(path):
            return None
        result = subprocess.check_output([path, "--version"], text=True)
        return result.splitlines()[0].split()[-1]

    @override
    def get_dependencies(self) -> list[str]:
        return []

    @override
    def get_latest_version(self) -> str:
        """Get latest binary release version from GitHub"""
        response = requests.get(
            "https://codeberg.org/api/v1/repos/ziglang/zig/tags?limit=1"
        )
        response.raise_for_status()
        return response.json()["name"]

    @override
    def install(self, version: str) -> None:
        """Install from pre-built binary tarball"""
        import tarfile

        # Download binary
        url = f"https://codeberg.org/ziglang/zig/archive/{version}.tar.gz"
        tarball_path = Path(self.config.paths.git_repos) / f"zig-{version}.tar.gz"

        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(tarball_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                _ = f.write(chunk)

        # Extract
        extract_path = Path(f"{self.config.paths.git_repos}/{self.tool_name}")
        extract_path.mkdir(parents=True, exist_ok=True)
        print(f"Extracting to {extract_path}...")

        with tarfile.open(tarball_path, "r:gz") as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts
                if len(parts) <= 1:
                    continue
                member.name = str(Path(*parts[1:]))
                tar.extract(member, path=extract_path)

        # Cleanup
        tarball_path.unlink()

        print(f"Zig {version} installed successfully")

    @override
    def update(self, version: str) -> None:
        """Update binary installation"""
        # Remove old version
        extract_path = Path(f"{self.config.paths.git_repos}/{self.tool_name}")
        if extract_path.exists():
            _ = subprocess.check_call(["sudo", "rm", "-rf", str(extract_path)])

        # Install new version
        self.install(version)

    @override
    def check_and_install(
        self, ghostty: bool = False, ghostty_version: str | None = None
    ):
        self.ghostty: bool = ghostty
        current = self.get_current_version()
        if ghostty_version:
            version = ghostty_version
        else:
            version = self.config.tools[self.tool_name].version
        if not version or version.lower() == "latest":
            version = self.get_latest_version()

        if not current:
            logger.info(f"Installing {self.tool_name}...")
            self.install(version)
            return

        if Version(current) < Version(version):
            logger.info(f"Updating {self.tool_name} from {current} to {version}...")
            self.update(version)
        else:
            logger.info(f"{self.tool_name} is up to date ({current})")
