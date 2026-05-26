from functools import cached_property
from pathlib import Path
from typing import cast

from git import Repo

from dotfilesforge import logger
from dotfilesforge.config import Config, get_config

PLATFORMS = ["github", "gitlab", "custom"]


# TODO: Config read in Repository to clone
class Dotfiles:
    def __init__(self, config: Config | None = None):
        self.config: Config = config or get_config()

    def get_repo_url(self) -> str:
        platform: str | None = cast(
            str | None, self.config.dotfiles.get("repo_host", None)
        )

        if platform is None or platform == "" or platform not in PLATFORMS:
            raise SystemExit(logger.error("No valid Platform configured."))

        repo_name: str | None = cast(
            str | None, self.config.dotfiles.get("repo_name", None)
        )
        if repo_name is None or repo_name == "":
            raise SystemExit(logger.error("No valid Repo Name configured."))

        host = self.config.dotfiles.get("repo_url", None)
        if platform == "custom" and host is None:
            raise SystemExit(logger.error("No Host for custom configured."))

        url = None
        domain = "https://"

        if self.config.dotfiles.get("repo_modus") == "ssh":
            domain = "git@"

        if platform == "github":
            url = f"{domain}github.com/{repo_name}"

        if platform == "gitlab":
            url = f"{domain}gitlab.com/{repo_name}"

        if platform == "custom":
            url = f"{domain}{host}/{repo_name}"

        if url is None:
            raise SystemExit(logger.error("No valid URL created."))

        return url

    @cached_property
    def install_path(self) -> Path:
        return Path(self.config.paths.dotfiles)

    def check_and_install(self):
        path = self.install_path

        if path.exists():
            self.update()
        else:
            self.install()

    def install(self) -> None:
        self._clone()

    def update(self) -> None:
        self._pull()

    def _clone(self) -> None:
        _ = Repo.clone_from(to_path=self.install_path, url=self.get_repo_url())

    def _pull(self) -> None:
        repo = Repo(self.install_path)
        _ = repo.git.stash("push", "-m", "Temp Stash for Updates")
        origin = repo.remotes.origin
        _ = origin.pull()
        _ = repo.git.stash("pop")
