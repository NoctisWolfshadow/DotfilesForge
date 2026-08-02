import shutil
import subprocess
import sys

from dotfilesforge.base_tool import GitBasedTool, ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.package_manager import get_package_manager
from dotfilesforge.tools.rustup import RustupInstaller

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class YaziInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("yazi")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("git", "default"):
            return YaziGitInstaller()
        if method == "package":
            return YaziPackageInstaller()
        else:
            raise ValueError(f"Unknown install method: '{method}'")


class YaziPackageInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "yazi"

    @override
    def get_dependencies(self) -> list[str]:
        package_manager = get_package_manager().getPackageManager()
        dependencies: list[str] = []
        if package_manager in ("pacman", "yay"):
            dependencies.extend(
                [
                    "ffmpeg",
                    "jq",
                    "ripgrep",
                    "zoxide",
                    "resvg",
                    "imagemagick",
                    "7zip",
                    "poppler",
                    "fd",
                    "yazi",
                ]
            )

        return dependencies

    @override
    def get_current_version(self) -> str | None:
        return None

    @override
    def get_latest_version(self) -> str:
        return ""

    @override
    def install(self, version: str):
        pass

    @override
    def update(self, version: str):
        pass


class YaziGitInstaller(GitBasedTool):
    @property
    @override
    def tool_name(self) -> str:
        return "yazi"

    @override
    def get_dependencies(self) -> list[str]:
        package_manager = get_package_manager().getPackageManager()
        dependencies = [
            "ffmpeg",
            "jq",
            "ripgrep",
            "zoxide",
            "resvg",
            "imagemagick",
            "7zip",
            "make",
            "gcc",
        ]
        if package_manager in ("pacman", "yay"):
            dependencies.append("fd")
            dependencies.append("poppler")
        if package_manager == "apt":
            dependencies.append("fd-find")
            dependencies.append("poppler-utils")
        return dependencies

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("yazi"):
            return None

        result = subprocess.check_output(["yazi", "--version"], text=True)
        return result.splitlines()[0].split()[1]

    @override
    def get_repo_url(self) -> str:
        return "https://github.com/sxyazi/yazi"

    @override
    def build(self) -> None:
        if not shutil.which("cargo"):
            rustup = RustupInstaller()
            rustup.check_and_install()
        _ = subprocess.check_call(
            ["cargo", "build", "--release", "--locked"], cwd=self.install_path
        )
        _ = subprocess.check_call(
            [
                "sudo",
                "mv",
                "target/release/yazi",
                "target/release/ya",
                "/usr/local/bin/",
            ],
            cwd=self.install_path,
        )

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
