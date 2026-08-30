import os
import shutil
import sys
from pathlib import Path
from typing import cast

import requests
from packaging.version import Version

from dotfilesforge import logger
from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


class ObsidianInstaller:
    def __new__(cls) -> ToolInstaller:
        config = get_config()
        tool_config = config.tools.get("neovim")
        method: str = (
            tool_config.install_method
            if tool_config and tool_config.install_method
            else "default"
        )

        if method in ("default", "appimage"):
            return ObsidianAppimageInstaller(config)
        else:
            raise ValueError(f"Unknown install method: {method}")


class ObsidianAppimageInstaller(ToolInstaller):
    @property
    @override
    def tool_name(self) -> str:
        return "obsidian"

    @property
    def path(self) -> Path:
        path: Path
        if isinstance(self.config.paths.appimages, Path):
            path = self.config.paths.appimages
        else:
            path = Path(self.config.paths.appimages).expanduser()

        path.mkdir(exist_ok=True, parents=True)
        return path

    @override
    def get_current_version(self) -> str | None:
        version: str | None = None
        for folder in self.path.iterdir():
            if "Obsidian" in folder.name:
                temp_version = folder.name.replace("Obsidian-", "").replace(
                    ".AppImage", ""
                )
                if not version or Version(version) < Version(temp_version):
                    version = temp_version
        return version

    @override
    def get_dependencies(self) -> list[str]:
        return []

    @override
    def get_latest_version(self) -> str:
        """Get latest binary release version from GitHub"""
        response = requests.get(
            "https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest"
        )
        response.raise_for_status()
        return response.json()["tag_name"]

    @override
    def install(self, version: str) -> None:

        self.clear_old_obsidian_install()
        self.download_appimage_file(version)

    @override
    def update(self, version: str) -> None:
        self.install(version)

    def clear_old_obsidian_install(self) -> None:
        for folder in self.path.iterdir():
            if folder.is_dir() and "Obsidian" in folder.name:
                shutil.rmtree(folder)

    def create_desktop_file(self):
        """Install or Update the Desktop File for new Versions"""
        appimage_dir = self.path

        # Find the Obsidian AppImage
        obsidian_appimage = None
        for file in appimage_dir.glob("Obsidian*.AppImage"):
            obsidian_appimage = file
            break

        if not obsidian_appimage:
            logger.error("Warning: No Obsidian AppImage found!")
            return

        desktop_file_path = Path.home() / ".local/share/applications/obsidian.desktop"
        desktop_file_path.parent.mkdir(parents=True, exist_ok=True)

        desktop_content = f"""
            [Desktop Entry]
            Name=Obsidian
            Exec={appimage_dir}/{obsidian_appimage.name} --no-sandbox %U
            Terminal=false
            Type=Application
            Icon={appimage_dir}/Icons/obsidian.png
            StartupWMClass=obsidian
            X-AppImage-Version={self.get_current_version()}
            Comment=Obsidian Editor
            MimeType=x-scheme-handler/obsidian;
            Categories=Office;
        """

        _ = desktop_file_path.write_text(desktop_content)
        logger.info("Updated or installed Desktop File for Obsidian")
        os.chmod(desktop_file_path, 0o755)
        os.chmod(obsidian_appimage, 0o755)

    def download_appimage_file(self, version: str) -> None:
        url = f"https://api.github.com/repos/obsidianmd/obsidian-releases/releases/tags/v{version}"
        response = requests.get(url, timeout=10)
        data = cast(dict[str, list[dict[str, str]]], response.json())
        file_content = None
        path = self.path

        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.endswith(".AppImage") and "arm64" not in name:
                path = path / name
                file_content = requests.get(asset["browser_download_url"], timeout=30)
                with open(path, "wb") as file:
                    _ = file.write(file_content.content)
