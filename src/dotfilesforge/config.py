import sys
from importlib.resources import files
from pathlib import Path
from typing import TypeAlias

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


TomlValue: TypeAlias = (
    str | int | float | bool | list["TomlValue"] | dict[str, "TomlValue"]
)


def load_toml_config() -> dict[str, TomlValue]:
    path = Path.home() / ".dotfiles" / "dotfilesforge.toml"
    if path.exists():
        with open(path, "rb") as file:
            toml = tomllib.load(file)
    else:
        with files("dotfilesforge").joinpath("dotfilesforge.toml").open("rb") as file:
            toml = tomllib.load(file)
    return toml
