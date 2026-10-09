from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
import tomllib
from functools import cache
from pathlib import Path
from typing import ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from dotfilesforge import logger
from dotfilesforge.representation import build_repr

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override


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


class PathConfig(BaseModel):
    dotfiles: Path = Field(default_factory=lambda: Path.home() / ".dotfiles")
    appimages: Path = Field(default_factory=lambda: Path.home() / "AppImages")
    git_repos: Path = Field(default_factory=lambda: Path.home() / "git")

    @override
    def __repr__(self) -> str:
        return build_repr(self)

    @field_validator("*", mode="after")
    @classmethod
    def _expand_user(cls, value: Path) -> Path:
        return value.expanduser()


class ToolConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    enabled: bool = False
    version: str | None = "latest"
    install_method: str = "default"


class SettingsConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", populate_by_name=True
    )

    shell: str | None = None
    wsl_exclude: list[str] = Field(default_factory=list)
    php_enabled: bool = Field(default=False, alias="php")


class Config(BaseModel):
    paths: PathConfig = Field(default_factory=PathConfig)
    packages: dict[str, list[str]] = Field(default_factory=dict)
    dotfiles_repo: dict[str, object] = Field(default_factory=dict)
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    tools: dict[str, ToolConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _finalize_tools(self) -> Config:
        wsl = is_wsl()
        for name, tool in self.tools.items():
            allowed = VALID_INSTALL_METHODS.get(name, frozenset({"default"}))
            if tool.install_method not in allowed:
                raise ValueError(
                    f"tools.{name}.install_method must be one of "
                    f"{sorted(allowed)}, got {tool.install_method!r}"
                )
            if wsl and name in self.settings.wsl_exclude:
                tool.enabled = False

        self.tools = {name: tool for name, tool in self.tools.items() if tool.enabled}
        if self.settings.php_enabled:
            self.tools["composer"] = ToolConfig(enabled=True)
        return self


def get_config(wsl: bool = False, url: str | None = None) -> Config:
    global _config
    if _config is None:
        try:
            _config = Config.model_validate(
                load_toml_config(url),
                context={"wsl": wsl or detect_wsl()},
            )
        except ValidationError as e:
            raise SystemExit(logger.error(f"Invalid config:\n{e}"))
    return _config


def get_toml_path(base_path: Path | None = None) -> Path | None:
    base_path = base_path or Path.home()
    candidates = [
        base_path / ".config" / "dotfilesforge" / "config.toml",
        base_path / ".dotfiles" / "dotfilesforge.toml",
        base_path / ".dotfiles" / ".config" / "dotfilesforge" / "config.toml",
        base_path / "dotfilesforge.toml",
    ]
    return next((path for path in candidates if path.exists()), None)


def load_toml_config(url: str | None = None) -> dict[str, object]:
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
            _ = subprocess.run(["git", "clone", url], cwd=tmp_dir)

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


@cache
def detect_wsl() -> bool:
    if "wsl" in platform.release().lower():
        return True
    if Path("/proc/sys/fs/binfmt_misc/WSLInterop").exists():
        return True
    return any("wsl" in key.lower() for key in os.environ)
