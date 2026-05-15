from typing import Callable

from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.tools.neovim import NeovimInstaller

_installers: list[ToolInstaller] | None = None

INSTALLER_MAP: dict[str, Callable[[], ToolInstaller]] = {
    "neovim": NeovimInstaller,
    # "ghostty": GhosttyInstaller,
}


def get_installers() -> list[ToolInstaller]:
    global _installers
    if _installers is None:
        _installers = [
            INSTALLER_MAP[name]()
            for name, tool in get_config().tools.items()
            if tool.enabled and name in INSTALLER_MAP
        ]
    return _installers
