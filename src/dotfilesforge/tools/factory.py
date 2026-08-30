from collections.abc import Callable

from dotfilesforge.base_tool import ToolInstaller
from dotfilesforge.config import get_config
from dotfilesforge.package_manager import get_package_manager
from dotfilesforge.tools.composer import ComposerInstaller
from dotfilesforge.tools.fzf import FzFInstaller
from dotfilesforge.tools.ghostty import GhosttyInstaller
from dotfilesforge.tools.laravel import LaravelInstaller
from dotfilesforge.tools.neovim import NeovimInstaller
from dotfilesforge.tools.obsidian import ObsidianInstaller
from dotfilesforge.tools.opencode import OpencodeInstaller
from dotfilesforge.tools.shell import get_shell
from dotfilesforge.tools.yazi import YaziInstaller

_installers: list[ToolInstaller] | None = None

INSTALLER_MAP: dict[str, Callable[[], ToolInstaller]] = {
    "neovim": NeovimInstaller,
    "ghostty": GhosttyInstaller,
    "opencode": OpencodeInstaller,
    "composer": ComposerInstaller,
    "yazi": YaziInstaller,
    "fzf": FzFInstaller,
    "laravel": LaravelInstaller,
    "obsidian": ObsidianInstaller,
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


def install_dependencies():
    installers = get_installers()
    package_manager = get_package_manager()
    packages: list[str] = []
    for installer in installers:
        packages.extend(installer.get_dependencies())

    packages = packages + package_manager.getPackages()
    shell = get_shell()
    if shell is not None:
        packages.append(shell.getPackage())

    _ = package_manager.install_packages(packages)
