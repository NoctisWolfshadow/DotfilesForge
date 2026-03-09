from abc import ABC, abstractmethod


class BaseTool(ABC):
    @abstractmethod
    def get_tool_name(self) -> str: ...


class ToolInstaller(BaseTool, ABC):
    def __init__(self, config: dict[str, str] | None = None):
        self.config: dict[str, str] = config or {}
        self.name: str = self.get_tool_name()
