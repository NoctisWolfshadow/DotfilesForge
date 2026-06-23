import sys
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

from git import Repo
from packaging.version import Version

from dotfilesforge import logger
from dotfilesforge.config import Config, get_config

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

VERSION_STRINGS = ["tip"]


class ToolInstaller(ABC):
    def __init__(self, config: Config | None = None):
        self.config: Config = config or get_config()

    @property
    @abstractmethod
    def tool_name(self) -> str: ...

    @abstractmethod
    def get_current_version(self) -> str | None: ...

    @abstractmethod
    def get_latest_version(self) -> str: ...

    @abstractmethod
    def get_dependecies(self) -> list[str]: ...

    @abstractmethod
    def install(self, version: str) -> None: ...

    @abstractmethod
    def update(self, version: str) -> None: ...

    def check_and_install(self) -> None:

        current = self.get_current_version()
        version = self.config.tools[self.tool_name].version
        if not version or version.lower() == "latest":
            version = self.get_latest_version()

        if not current:
            logger.info(f"Installing {self.tool_name}...")
            self.install(version)
            return

        if version in VERSION_STRINGS or Version(current) < Version(version):
            logger.info(f"Updating {self.tool_name} from {current} to {version}...")
            self.update(version)
        else:
            logger.info(f"{self.tool_name} is up to date ({current})")


class GitBasedTool(ToolInstaller, ABC):
    @abstractmethod
    def get_repo_url(self) -> str: ...

    @abstractmethod
    def build(self) -> None: ...

    @cached_property
    def install_path(self) -> Path:
        return Path(self.config.paths.git_repos) / self.tool_name

    @override
    def install(self, version: str) -> None:
        path = self.install_path
        if path.exists():
            return
        self._clone()
        self._checkout(version)
        self.build()

    @override
    def update(self, version: str) -> None:
        self._pull_tags()
        self._checkout(version)
        self.build()

    def _clone(self) -> None:
        _ = Repo.clone_from(to_path=self.install_path, url=self.get_repo_url())

    def _pull_tags(self) -> None:
        repo = Repo(self.install_path)
        origin = repo.remotes.origin
        _ = origin.fetch(tags=True, prune=True, force=True)

    def _checkout(self, version: str) -> None:
        repo = Repo(self.install_path)
        _ = repo.git.execute(["git", "checkout", version])
