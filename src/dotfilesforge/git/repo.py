from pathlib import Path
from typing import cast

from dulwich import porcelain
from dulwich.errors import NotGitRepository
from dulwich.repo import Repo as DW_Repo
from dulwich.stash import Stash as DW_Stash


class Repo:
    def __init__(self, path: Path | None = None):
        self.path: Path | None = path
        self._repo: DW_Repo | None = None

    @property
    def repo(self) -> DW_Repo:
        if self._repo is None:
            if self.path is None:
                raise ValueError("No repository path set.")
            self._repo = DW_Repo(self.path)
        return self._repo

    @staticmethod
    def is_repo(path: Path) -> bool:
        try:
            with DW_Repo(path):
                return True
        except NotGitRepository:
            return False

    def pull(
        self,
        location: str | None = None,
        branches: list[str] | str | None = None,
    ) -> None:
        porcelain.pull(
            repo=self.repo,
            remote_location=location,
            refspecs=branches,
        )

    def fetch(
        self,
        include_tags: bool = False,
        prune: bool = False,
        prune_tags: bool = False,
        force: bool = False,
    ) -> None:
        _ = porcelain.fetch(
            repo=self.repo,
            include_tags=include_tags,
            prune=prune,
            prune_tags=prune_tags,
            force=force,
        )

    def is_dirty(self, include_untracked: bool = False) -> bool:
        status = porcelain.status(self.repo)

        staged = cast(dict[str, list[bytes]], status.staged)
        unstaged = cast(list[bytes], status.unstaged)
        untracked = cast(list[str], status.untracked)

        # staged is a dict: {"add": [...], "delete": [...], "modify": [...]}
        if any(staged.values()):
            return True

        # tracked files modified or deleted in the working tree but not staged
        if unstaged:
            return True

        if include_untracked and untracked:
            return True

        return False

    def push(
        self,
        location: str | None = None,
        branches: list[str] | str | None = None,
    ) -> None:
        _ = porcelain.push(
            repo=self.repo,
            remote_location=location,
            refspecs=branches,
        )

    def checkout(self, version: str) -> None:
        porcelain.checkout(repo=self.repo, target=version)

    def clone(self, url: str, target: str | None | Path = None) -> None:
        target = target or self.path
        self._repo = porcelain.clone(source=url, target=target)

    def diff(self):
        pass

    def stash_push(
        self, message: str | bytes | None = "Temp Stash for Updates"
    ) -> None:
        stash: DW_Stash = DW_Stash.from_repo(self.repo)
        msg: bytes | None = None
        if message:
            if isinstance(message, str):
                msg = message.encode("utf-8")
            else:
                msg = message

        _ = stash.push(message=msg)

    def stash_pop(self) -> None:
        stash: DW_Stash = DW_Stash.from_repo(self.repo)

        _ = stash.pop(index=0)
