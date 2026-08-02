import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import cast

import requests

from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class FzFInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("fzf")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("bin", "default"):
            return FzFBinaryInstaller()
        if method == "package":
            return FzFPackageInstaller()
        else:
            raise ValueError(f"Unknown install method: '{method}'")


class FzFPackageInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "fzf"

    @override
    def get_dependencies(self) -> list[str]:
        return ["fzf"]

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


class FzFBinaryInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "fzf"

    @override
    def get_dependencies(self) -> list[str]:
        return []

    @override
    def get_current_version(self) -> str | None:
        if not shutil.which("fzf"):
            return None
        result = subprocess.check_output(["fzf", "--version"], text=True)
        return result.splitlines()[0].split()[-1]

    @override
    def get_latest_version(self) -> str:
        response = requests.get(
            "https://api.github.com/repos/junegunn/fzf/releases/latest"
        )
        response.raise_for_status()
        return response.json()["tag_name"]

    @override
    def install(self, version: str):

        download_path = Path.home() / "Downloads" / "fzf"
        filepath = self.download_tar_file(version, download_path)
        _ = self.extract_tar(filepath, download_path)

    @override
    def update(self, version: str):
        download_path = Path.home() / "Downloads" / "fzf"
        filepath = self.download_tar_file(version, download_path)
        _ = self.extract_tar(filepath, download_path)

    def download_tar_file(self, version: str, path: Path) -> Path:
        url = f"https://api.github.com/repos/junegunn/fzf/releases/tags/v{version}"
        response = requests.get(url, timeout=10)
        data = cast(dict[str, list[dict[str, str]]], response.json())
        file_content = None
        path.mkdir(parents=True, exist_ok=True)
        for asset in data.get("assets", []):
            if "linux_amd64" in asset["name"]:
                path = path / asset["name"]
                file_content = requests.get(asset["browser_download_url"], timeout=30)
                with open(path, "wb") as file:
                    _ = file.write(file_content.content)
        return path

    def extract_tar(self, filepath: Path, extract_path: Path) -> None:
        with tarfile.open(filepath, "r:gz") as tar:
            tar.extractall(extract_path)
        # print(asset["name"], asset["browser_download_url"])
        bin_path = extract_path / "fzf"
        _ = subprocess.check_call(
            ["mv", bin_path.as_posix(), Path.home() / ".local" / "bin"]
        )
        shutil.rmtree(extract_path)
