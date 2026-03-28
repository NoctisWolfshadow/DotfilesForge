from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias, cast

from dotfilesforge import logger

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


@dataclass
class PathConfig:
    dotfiles: Path | str = field(default_factory=lambda: Path.home() / ".dotfiles")
    appimages: Path | str = field(
        default_factory=lambda: Path.home() / ".dotfiles" / "AppImage"
    )
    git_repos: Path | str = field(default_factory=lambda: Path.home() / "git")

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

    @classmethod
    def from_raw(cls, data: dict[str, str | bool | None], name: str) -> ToolConfig:
        enabled = data.get("enabled", False)
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

    @override
    def __repr__(self):
        return f"Config(paths={self.paths!r}, tools={self.tools!r})"


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config(load_toml_config())
    return _config


def get_toml_path() -> Path | None:
    candidates = [
        Path.home() / ".dotfiles" / "dotfilesforge.toml",
        Path.home() / ".config" / "dotfilesforge" / "config.toml",
    ]
    return next((path for path in candidates if path.exists()), None)


def load_toml_config() -> dict[str, TomlValue]:
    path = get_toml_path()
    if path:
        with open(path, "rb") as file:
            toml = tomllib.load(file)
    else:
        raise SystemExit(logger.error("No Config file found. Exiting..."))
    return toml
