from __future__ import annotations

import os
import platform
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias, cast

import git

from dotfilesforge import logger
from dotfilesforge.representation import build_repr

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

TomlValue: TypeAlias = (
    str | int | float | bool | list["TomlValue"] | dict[str, "TomlValue"]
)

VALID_INSTALL_METHODS: dict[str, frozenset[str]] = {
    "neovim": frozenset({"default", "package", "git", "bin"}),
    "ghostty": frozenset({"default", "package", "git", "bin"}),
    "yazi": frozenset({"default", "package", "git", "bin"}),
}

_config: Config | None = None
_wsl: bool = False


@dataclass
class PathConfig:
    dotfiles: Path | str = field(default_factory=lambda: Path.home() / ".dotfiles")
    appimages: Path | str = field(
        default_factory=lambda: Path.home() / ".dotfiles" / "AppImage"
    )
    git_repos: Path | str = field(default_factory=lambda: Path.home() / "git")

    @override
    def __repr__(self) -> str:
        return build_repr(self)

    def __post_init__(self):
        for path in self.__dataclass_fields__:
            value: Path | str = cast(Path | str, getattr(self, path))
            if isinstance(value, str):
                setattr(self, path, Path(value).expanduser())


@dataclass
class ToolConfig:
    enabled: bool = False
    version: str | None = None
    install_method: str = "default"

    @override
    def __repr__(self) -> str:
        return build_repr(self)

    @classmethod
    def from_raw(cls, data: dict[str, str | bool | None], name: str) -> ToolConfig:
        enabled = data.get("enabled", False)
        global _wsl
        if data.get("wsl", True) == False and _wsl:
            enabled = False

        if not isinstance(enabled, bool):
            raise SystemExit(
                logger.error(
                    f"Invalid config ({name}): 'enabled' must be a bool, got {type(enabled).__name__!r} ({enabled!r})"
                )
            )

        version = data.get("version", "latest")
        if version is not None and not isinstance(version, str):
            raise SystemExit(
                logger.error(
                    f"Invalid config ({name}): 'version' must be a string or null, got {type(version).__name__!r}"
                )
            )

        install_method = data.get("install_method", "default")
        if (
            not isinstance(install_method, str)
            or install_method not in VALID_INSTALL_METHODS[name]
        ):
            raise SystemExit(
                logger.error(
                    f"Invalid config ({name}): 'install_method' must be one of {VALID_INSTALL_METHODS[name]}, got {install_method!r}"
                )
            )

        return cls(enabled=enabled, version=version, install_method=install_method)


class Config:
    def __init__(self, toml: dict[str, TomlValue]):
        self.paths: PathConfig = PathConfig(
            **(cast(dict[str, str], toml.get("paths", {})))
        )
        tools_raw = cast(dict[str, dict[str, str | bool | None]], toml.get("tools", {}))
        self.tools: dict[str, ToolConfig] = {
            name: tool
            for name, data in tools_raw.items()
            if (tool := ToolConfig.from_raw(data, name)).enabled
        }
        self.packages: dict[str, list[str]] = cast(
            dict[str, list[str]], toml.get("packages", {})
        )
        self.dotfiles: dict[str, TomlValue] = cast(
            dict[str, TomlValue], toml.get("dotfiles", {})
        )
        self.services: dict[str, TomlValue] = cast(
            dict[str, TomlValue], toml.get("services", {})
        )

    @override
    def __repr__(self) -> str:
        return build_repr(self)


def get_config(url: str | None = None) -> Config:
    global _config
    if _config is None:
        _config = Config(load_toml_config(url))
    return _config


def get_toml_path() -> Path | None:
    candidates = [
        Path.home() / ".dotfiles" / "dotfilesforge.toml",
        Path.home() / ".config" / "dotfilesforge" / "config.toml",
    ]
    return next((path for path in candidates if path.exists()), None)


def load_toml_config(url: str | None = None) -> dict[str, TomlValue]:
    path = get_toml_path()
    toml = None
    if path and url is None:
        with open(path, "rb") as file:
            toml = tomllib.load(file)
    if url:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _ = git.Repo.clone_from(url, tmp_dir)

            remote_config = Path(tmp_dir) / "dotfilesforge.toml"
            if not remote_config.exists():
                raise SystemExit(
                    logger.error(
                        f"'dotfilesforge.toml' not found in repository '{url}'."
                    )
                )

            with open(remote_config, "rb") as f:
                toml = tomllib.load(f)

    if toml is None:
        raise SystemExit(logger.error("No Config file found. Exiting..."))
    return toml


def set_wsl(wsl: bool) -> None:
    global _wsl
    if wsl:
        print("Option\n")
        _wsl = wsl
        return
    check_if_wsl()


def check_if_wsl() -> None:
    """
    From inside the Linux terminal:Check kernel version (Fastest): Run uname -a or cat /proc/version.
    If the output contains Microsoft or -WSL, you are in WSL.
    Check environment variables: Run env | grep -i wsl.
    If it returns WSL_DISTRO_NAME or WSL_INTEROP, WSL is active.
    Check system files: Look for the WSL interoperability file with ls -la /proc/sys/fs/binfmt_misc/WSLInterop.
    Its presence confirms a WSL environment.
    """
    global _wsl

    if _wsl:
        return

    proc_version: str = platform.release()
    if proc_version.find("wsl"):
        _wsl = True
        return

    interop_file = Path("/proc/sys/fs/binfmt_misc/WSLInterop")
    if interop_file.exists():
        _wsl = True
        return

    wsl_vars = {k: v for k, v in os.environ.items() if "wsl" in k.lower()}
    if wsl_vars:
        _wsl = True
        return
