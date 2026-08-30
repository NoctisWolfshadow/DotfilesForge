from __future__ import annotations

import os
import platform
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias, TypedDict, cast

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
    "ghostty": frozenset({"default", "package", "git"}),
    "opencode": frozenset({"default", "bin"}),
    "composer": frozenset({"default"}),
    "fzf": frozenset({"default", "package", "bin"}),
    "rustup": frozenset({"default", "script"}),
    "yazi": frozenset({"default", "package", "git"}),
    "laravel": frozenset({"default", "composer"}),
    "zig": frozenset({"default", "bin"}),
    "obsidian": frozenset({"default", "appimage"}),
}

_config: Config | None = None
_wsl: bool = False


@dataclass
class PathConfig:
    dotfiles: Path | str = field(default_factory=lambda: Path.home() / ".dotfiles")
    appimages: Path | str = field(default_factory=lambda: Path.home() / "AppImages")
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
    def from_raw(
        cls,
        data: dict[str, str | bool | None],
        name: str,
        wsl_excluded: list[str],
    ) -> ToolConfig:
        enabled = data.get("enabled", False)
        global _wsl
        if name in wsl_excluded and _wsl:
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
                    f"Invalid config ({name}): 'install_method' must be one of {', '.join(VALID_INSTALL_METHODS[name])!r} got {install_method!r}"
                )
            )

        return cls(enabled=enabled, version=version, install_method=install_method)


@dataclass
class SettingsConfig:
    class RawData(TypedDict, total=False):
        shell: str | None
        php: bool
        wsl_exclude: list[str]

    shell: str | None = None
    wsl_exclude: list[str] = field(default_factory=list)
    php_enabled: bool = False

    @override
    def __repr__(self) -> str:
        return build_repr(self)

    @classmethod
    def from_raw(cls, data: RawData) -> SettingsConfig:
        return cls(
            shell=data.get("shell"),
            php_enabled=data.get("php", False),
            wsl_exclude=data.get("wsl_exclude", []),
        )


class Config:
    def __init__(self, toml: dict[str, TomlValue]):
        self.paths: PathConfig = PathConfig(
            **(cast(dict[str, str], toml.get("paths", {})))
        )

        self.packages: dict[str, list[str]] = cast(
            dict[str, list[str]], toml.get("packages", {})
        )

        self.dotfiles_repo: dict[str, TomlValue] = cast(
            dict[str, TomlValue], toml.get("dotfiles_repo", {})
        )

        self.settings: SettingsConfig = SettingsConfig.from_raw(
            cast(SettingsConfig.RawData, toml.get("settings", {}))
        )

        tools_raw = cast(dict[str, dict[str, str | bool | None]], toml.get("tools", {}))
        self.tools: dict[str, ToolConfig] = {
            name: tool
            for name, data in tools_raw.items()
            if (
                tool := ToolConfig.from_raw(data, name, self.settings.wsl_exclude)
            ).enabled
        }

        if self.settings.php_enabled is True:
            self.tools["composer"] = ToolConfig(True, "latest")

    @override
    def __repr__(self) -> str:
        return build_repr(self)


def get_config(wsl: bool = False, url: str | None = None) -> Config:
    set_wsl(wsl)
    global _config
    if _config is None:
        _config = Config(load_toml_config(url))
    return _config


def get_toml_path(base_path: Path | None = None) -> Path | None:
    base_path = base_path or Path.home()
    candidates = [
        base_path / ".dotfiles" / "dotfilesforge.toml",
        base_path / ".config" / "dotfilesforge" / "config.toml",
        base_path / "dotfilesforge.toml",
    ]
    return next((path for path in candidates if path.exists()), None)


def load_toml_config(url: str | None = None) -> dict[str, TomlValue]:
    path = get_toml_path()
    toml = None
    if path and url is None:
        with open(path, "rb") as file:
            try:
                toml = tomllib.load(file)
            except tomllib.TOMLDecodeError as e:
                logger.error(f"Failed to parse '{path}': {e}")
    if url:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _ = git.Repo.clone_from(url, tmp_dir)

            remote_config: Path | None = get_toml_path(Path(tmp_dir))

            if not remote_config:
                raise SystemExit(
                    logger.error(
                        f"'dotfilesforge.toml' not found in repository '{url}'."
                    )
                )

            with open(remote_config, "rb") as file:
                try:
                    toml = tomllib.load(file)
                except tomllib.TOMLDecodeError as e:
                    logger.error(f"Failed to parse '{remote_config}': {e}")

    if toml is None:
        raise SystemExit(logger.error("No Config file found. Exiting..."))
    return toml


def set_wsl(wsl: bool) -> None:
    global _wsl
    if wsl:
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

    proc_version: str = platform.release().lower()
    if "wsl" in proc_version:
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
