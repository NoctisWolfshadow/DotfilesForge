import sys
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import TypeAlias, cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


TomlValue: TypeAlias = (
    str | int | float | bool | list["TomlValue"] | dict[str, "TomlValue"]
)


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


@dataclass
class Config:
    def __init__(self, toml: dict[str, TomlValue]):
        self.paths: PathConfig = PathConfig(
            **(cast(dict[str, str], toml.get("paths", {})))
        )
        tools_raw = cast(dict[str, dict[str, str | bool | None]], toml.get("tools", {}))
        self.tools: dict[str, ToolConfig] = {
            name: ToolConfig(
                enabled=cast(bool, data.get("enabled")),
                version=cast(str | None, data.get("version")),
                install_method=cast(str, data.get("install_method", "default")),
            )
            for name, data in tools_raw.items()
        }


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config(load_toml_config())
    return _config


def load_toml_config() -> dict[str, TomlValue]:
    path = Path.home() / ".dotfiles" / "dotfilesforge.toml"
    if path.exists():
        with open(path, "rb") as file:
            toml = tomllib.load(file)
    else:
        with files("dotfilesforge").joinpath("dotfilesforge.toml").open("rb") as file:
            toml = tomllib.load(file)
    return toml
