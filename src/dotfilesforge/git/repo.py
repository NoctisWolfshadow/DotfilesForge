from pathlib import Path
from typing import cast

from dulwich import porcelain
from dulwich.errors import NotGitRepository
from dulwich.objects import S_ISGITLINK
from dulwich.repo import Repo as DW_Repo
from dulwich.stash import Stash as DW_Stash


class Repo:
    def __init__(self, path: Path | None = None):
        self.path: Path | None = path
        self._repo: DW_Repo | None = None

    def close(self) -> None:
        if self._repo is not None:
            self._repo.close()
            self._repo = None

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

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
        remote_location: bytes | str = "origin",
    ) -> None:
        _ = porcelain.fetch(
            repo=self.repo,
            include_tags=include_tags,
            prune=prune,
            prune_tags=prune_tags,
            force=force,
            remote_location=remote_location,
        )

    def _submodule_paths(self) -> set[bytes]:
        index = self.repo.open_index()
        return {
            path
            for path, entry in index.iteritems()
            if S_ISGITLINK(getattr(entry, "mode", 0))
        }

    def is_dirty(self, include_untracked: bool = False) -> bool:
        status = porcelain.status(self.repo)
        submodules = self._submodule_paths()

        staged = cast(dict[str, list[bytes]], status.staged)
        unstaged = cast(list[bytes], status.unstaged)
        untracked = cast(list[str], status.untracked)

        def real(paths: list[str] | list[bytes]) -> list[bytes]:
            out: list[bytes] = []
            for path in paths:
                if isinstance(path, str):
                    path = path.encode()
                if path.rstrip(b"/") not in submodules:
                    out.append(path)
            return out

        # staged is a dict: {"add": [...], "delete": [...], "modify": [...]}
        if any(real(files) for files in staged.values()):
            return True

        # tracked files modified or deleted in the working tree but not staged
        if real(unstaged):
            return True

        if include_untracked and real(untracked):
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
