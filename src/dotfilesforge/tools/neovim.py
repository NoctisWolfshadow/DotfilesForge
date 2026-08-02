import shutil
import subprocess
import sys
from pathlib import Path

import requests

from dotfilesforge.base_tool import GitBasedTool, ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.package_manager import get_package_manager

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class NeovimInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("neovim")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("git", "default"):
            return NeovimGitInstaller(config)
        elif method == "bin":
            return NeovimBinaryInstaller(config)
        else:
            raise ValueError(f"Unknown install method: {method}")


class NeovimBinaryInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "neovim"

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("nvim"):
            return None
        result = subprocess.check_output(["nvim", "--version"], text=True)
        return result.splitlines()[0].split()[-1]

    @override
    def get_dependencies(self) -> list[str]:
        return []

    @override
    def get_latest_version(self) -> str:
        """Get latest binary release version from GitHub"""
        response = requests.get(
            "https://api.github.com/repos/neovim/neovim/releases/latest"
        )
        response.raise_for_status()
        return response.json()["tag_name"]

    @override
    def install(self, version: str) -> None:
        """Install from pre-built binary tarball"""
        import tarfile

        # Download binary
        url = f"https://github.com/neovim/neovim/releases/download/{version}/nvim-linux64.tar.gz"
        tarball_path = Path.home() / f"nvim-{version}.tar.gz"

        print(f"Downloading {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(tarball_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                _ = f.write(chunk)

        # Extract
        extract_path = Path("/opt/nvim")
        print(f"Extracting to {extract_path}...")

        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=extract_path.parent)

        # Create symlink
        _ = subprocess.check_call(
            [
                "sudo",
                "ln",
                "-sf",
                str(extract_path / "bin" / "nvim"),
                "/usr/local/bin/nvim",
            ]
        )

        # Cleanup
        tarball_path.unlink()

        print(f"Neovim {version} installed successfully")

    @override
    def update(self, version: str) -> None:
        """Update binary installation"""
        # Remove old version
        extract_path = Path("/opt/nvim")
        if extract_path.exists():
            _ = subprocess.check_call(["sudo", "rm", "-rf", str(extract_path)])

        # Install new version
        self.install(version)


class NeovimGitInstaller(GitBasedTool):
    """Install Neovim from Git source"""

    @property
    @override
    def tool_name(self) -> str:
        return "neovim"

    @override
    def get_repo_url(self) -> str:
        return "https://github.com/neovim/neovim.git"

    @override
    def get_dependencies(self) -> list[str]:
        package_manager = get_package_manager().getPackageManager()
        packages = []
        if package_manager == "pacman" or package_manager == "yay":
            packages = ["base-devel", "ninja"]

        if package_manager == "apt":
            packages = ["build-essential", "ninja-build"]

        return packages

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("nvim"):
            return None
        result = subprocess.check_output(["nvim", "--version"], text=True)
        return result.splitlines()[0].split()[-1]

    @override
    def get_latest_version(self) -> str:
        tags = subprocess.check_output(
            [
                "git",
                "ls-remote",
                "--tags",
                "--refs",
                "--sort=v:refname",
                self.get_repo_url(),
            ],
            text=True,
        )

        if not tags:
            raise RuntimeError("No version tags found")

        latest = None
        for tag in tags.strip().split("\n"):
            if "refs/tags/v" in tag:
                latest = tag.split("/")[-1]

        if not latest:
            raise RuntimeError("No version tag found")

        return latest

    @override
    def build(self) -> None:
        """Build Neovim from source"""
        path = self.install_path
        _ = subprocess.check_call(["make", "CMAKE_BUILD_TYPE=RelWithDebInfo"], cwd=path)
        _ = subprocess.check_call(["sudo", "make", "install"], cwd=path)
