import shutil
import subprocess
import sys
from pathlib import Path

import requests
from packaging.version import Version

from dotfilesforge import logger
from dotfilesforge.base_tool import GitBasedTool, ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.package_manager import get_package_manager
from dotfilesforge.tools.zig import ZigInstaller

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class GhosttyInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("ghostty")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "git"
        )

        if method in ("git", "default"):
            return GhosttyGitInstaller(config)
        elif method == "bin":
            return GhosttyBinaryInstaller(config)
        else:
            raise ValueError(f"Unknown install method: {method}")


class GhosttyPackageInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "ghostty"

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("ghostty"):
            return None
        result = subprocess.check_output(["ghostty", "+version"], text=True)
        return result.splitlines()[0].split()[-1]

    @override
    def get_dependecies(self) -> list[str]:
        return []

    @override
    def get_latest_version(self) -> str:
        """Get latest binary release version from GitHub"""
        response = requests.get(
            "https://api.github.com/repos/ghostty/ghostty/releases/latest"
        )
        response.raise_for_status()
        return response.json()["tag_name"]

    @override
    def install(self, version: str) -> None:
        """Install from pre-built binary tarball"""
        import tarfile

        # Download binary
        url = f"https://github.com/ghostty-org/ghostty/releases/download/{version}/nvim-linux64.tar.gz"
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


class GhosttyGitInstaller(GitBasedTool):
    """Install Ghostty from Git source"""

    VERSION_MAP: list[tuple[str, str]] = [
        ("1.2", "0.13.0"),
        ("1.3", "0.14.1"),
        ("1.4", "0.15.2"),
    ]

    @property
    @override
    def tool_name(self) -> str:
        return "ghostty"

    @override
    def get_repo_url(self) -> str:
        return "https://github.com/ghostty-org/ghostty.git"

    @override
    def get_dependecies(self) -> list[str]:
        package_manager = get_package_manager().getPackageManager()
        packages = []
        if package_manager == "pacman" or package_manager == "yay":
            packages = ["gtk4", "gtk4-layer-shell", "libadwaita", "gettext"]

        if package_manager == "apt":
            packages = [
                "libgtk-4-dev",
                "libgtk4-layer-shell-dev",
                "libadwaita-1-dev",
                "gettext",
                "libxml2-utils",
            ]

        return packages

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("ghostty"):
            return None
        result = subprocess.check_output(["ghostty", "+version"], text=True)
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
        """Build Ghostty from source"""
        zig = ZigInstaller()
        zig.check_and_install(True, self.zig_version)
        path = self.install_path
        _ = subprocess.check_call(["make", "CMAKE_BUILD_TYPE=RelWithDebInfo"], cwd=path)
        _ = subprocess.check_call(["sudo", "make", "install"], cwd=path)

    def get_zig_version(self, ghostty_version: str) -> None:
        if ghostty_version.lower() == "tip":
            self.zig_version: str = "0.15.2"
            return

        ghostty_version_local: Version = Version(ghostty_version)

        for max_ghostty_version, zig_version_local in self.VERSION_MAP:
            if ghostty_version_local < Version(max_ghostty_version):
                self.zig_version = zig_version_local
                return

        raise SystemExit(logger.error("No fitting Zig version found for Ghostty"))

    def get_modversion_pkgconf(self, package: str) -> str:
        pkg_command: str | None = None
        if shutil.which("pkg-config") is not None:
            pkg_command = "pkg-config"
        if shutil.which("pkgconf") is not None:
            pkg_command = "pkgconf"

        if pkg_command is None:
            raise SystemExit(logger.error("Can't check version of installed packages"))

        version: str | None = None
        try:
            res = subprocess.run(
                [pkg_command, "--modversion", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if res.returncode == 0:
                version = res.stdout.strip()
        except Exception:
            raise SystemExit(logger.error(f"Error when getting the {package} version"))

        if version is None:
            raise SystemExit(logger.error("No available Version found"))

        return version

    def installable_ghostty_version(self, use_tip: bool) -> str:
        installable_version: str | None = None
        version = {
            "libadwaita": self.get_modversion_pkgconf("libadwaita-1"),
            "gtk": self.get_modversion_pkgconf("gtk4"),
        }

        if Version(version["libadwaita"]) < Version("1.2") and Version(
            version["gtk"]
        ) < Version("4.8"):
            installable_version = "v1.0.1"
        if Version(version["libadwaita"]) < Version("1.5") and Version(
            version["gtk"]
        ) < Version("4.14"):
            installable_version = "v1.1.3"
        elif use_tip:
            installable_version = "tip"
        else:
            installable_version = self.get_latest_version()

        return installable_version

    @override
    def check_and_install(self) -> None:

        current = self.get_current_version()
        version = self.config.tools[self.tool_name].version
        if not version or version.lower() == "latest":
            version = self.installable_ghostty_version(False)
        if not version or version.lower() == "tip":
            version = self.installable_ghostty_version(True)

        self.get_zig_version(version)
        print(self.zig_version)
        raise SystemExit()
        if not current:
            logger.info(f"Installing {self.tool_name}...")
            self.install(version)
            return

        if Version(current) < Version(version):
            logger.info(f"Updating {self.tool_name} from {current} to {version}...")
            self.update(version)
        else:
            logger.info(f"{self.tool_name} is up to date ({current})")
