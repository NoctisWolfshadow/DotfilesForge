from functools import cached_property
from pathlib import Path
from typing import cast

from stow_python import StowConfig, stow

from dotfilesforge import logger
from dotfilesforge.config import Config, get_config
from dotfilesforge.git.repo import Repo

PLATFORMS = ["github", "gitlab", "custom"]


# TODO: Config read in Repository to clone
class Dotfiles:
    def __init__(self, config: Config | None = None):
        self.config: Config = config or get_config()
        self.repo: Repo = Repo(self.install_path)

    def get_repo_url(self) -> str:
        platform: str | None = cast(
            str | None, self.config.dotfiles_repo.get("repo_host", None)
        )

        if platform is None or platform == "" or platform not in PLATFORMS:
            raise SystemExit(logger.error("No valid Platform configured."))

        repo_name: str | None = cast(
            str | None, self.config.dotfiles_repo.get("repo_name", None)
        )
        if repo_name is None or repo_name == "":
            raise SystemExit(logger.error("No valid Repo Name configured."))

        host = self.config.dotfiles_repo.get("repo_url", None)
        if platform == "custom" and host is None:
            raise SystemExit(logger.error("No Host for custom configured."))

        url = None
        prefix = "https://"

        if self.config.dotfiles_repo.get("repo_modus") == "ssh":
            prefix = "git@"

        sep = ":" if prefix == "git@" else "/"

        if platform == "github":
            url = f"{prefix}github.com{sep}{repo_name}"

        if platform == "gitlab":
            url = f"{prefix}gitlab.com{sep}{repo_name}"

        if platform == "custom":
            url = f"{prefix}{host}{sep}{repo_name}"

        if url is None:
            raise SystemExit(logger.error("No valid URL created."))

        return url

    @cached_property
    def install_path(self) -> Path:
        return Path(self.config.paths.dotfiles)

    def check_and_install(self) -> None:
        path = self.install_path

        if not self._has_repo_url() or not self._is_git_repo():
            logger.warn("Has no Repo configured. Falling back to local Instance.")
            return

        if path.exists():
            self.update()
            self.stow_files()
        else:
            self.install()
            self.stow_files()

    def stow_files(self):
        target_stow: str = Path.home().as_posix()
        dir_stow: str = self.install_path.as_posix()
        config: StowConfig = StowConfig(dir=dir_stow, target=target_stow, dotfiles=True)
        _ = stow(".", config=config)

    def _has_repo_url(self) -> bool:
        try:
            _ = self.get_repo_url()
            return True
        except:
            return False

    def _is_git_repo(self) -> bool:
        return Repo.is_repo(self.install_path)

    def install(self) -> None:
        self._clone()

    def update(self) -> None:
        self._pull()

    def _clone(self) -> None:
        self.repo.clone(url=self.get_repo_url(), target=self.install_path)

    def _pull(self) -> None:
        has_changes = self.repo.is_dirty()

        if has_changes:
            logger.info("Create Temporary Stash")
            self.repo.stash_push(message="Temp Stash for Updates")

        self.repo.pull()

        if has_changes:
            logger.info("Popping Temporary Stash")
            self.repo.stash_pop()
