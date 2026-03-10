from abc import ABC, abstractmethod

from packaging.version import Version


class BaseTool(ABC):
    @abstractmethod
    def get_tool_name(self) -> str: ...


class ToolInstaller(BaseTool, ABC):
    def __init__(self, config: dict[str, str] | None = None):
        self.config: dict[str, str] = config or {}
        self.name: str = self.get_tool_name()

    @abstractmethod
    def get_current_version(self) -> str | None: ...

    @abstractmethod
    def get_latest_version(self) -> str: ...

    @abstractmethod
    def install(self, version: str) -> None: ...

    @abstractmethod
    def update(self, version: str) -> None: ...

    def check_and_install(self) -> None:

        current = self.get_current_version()
        latest = self.get_latest_version()

        if not current:
            print(f"Installing {self.name}...")
            self.install(latest)
            return

        if Version(current) < Version(latest):
            print(f"Updating {self.name} from {current} to {latest}...")
            self.update(latest)
        else:
            print(f"{self.name} is up to date ({current})")
