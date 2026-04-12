import shutil
from dataclasses import dataclass

from dotfilesforge.config import Config, get_config
from src.dotfilesforge import logger

COMMAND_LIST: dict[str, dict[str, list[str]]] = {
    "pacman": {
        "install": ["sudo", "pacman", "-S"],
        "update": ["sudo", "pacman", "-Syu"],
        "search": ["pacman", "-Ss"],
    },
    "yay": {
        "install": ["yay", "-S"],
        "update": ["yay", "-Syu"],
        "search": ["yay", "-Ss"],
    },
    "apt": {
        "install": ["sudo", "apt", "install"],
        "update": ["sudo", "apt", "update", "&&", "sudo", "apt", "upgrade", "-y"],
        "search": ["apt", "search"],
    },
}


@dataclass
class PackageManager:
    def __init__(self, config: Config):
        self.package_manager: str = self.getPackageManager()
        self.commands: dict[str, list[str]] = COMMAND_LIST[self.package_manager]
        self.config: Config = config or get_config()

    def getUpdate(self) -> list[str]:
        return self.commands["update"]

    def getInstall(self) -> list[str]:
        return self.commands["install"]

    def searchPackage(self) -> list[str]:
        return self.commands["search"]

    def addPackages(self, method: list[str]):
        package_manager = self.package_manager
        packages: list[str] = self.config.packages[self.package_manager]
        if package_manager == "yay":
            packages = self.config.packages["pacman"] + packages

        return method + packages

    def getPackageManager(self) -> str:
        if shutil.which("pacman"):
            if shutil.which("yay"):
                return "yay"
            return "pacman"

        raise SystemExit(logger.error("No valid Package Manager found."))
