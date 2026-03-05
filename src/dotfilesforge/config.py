import sys
from pathlib import Path

from typing_extensions import TypeAlias

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
        print("No Config File found for DotfilesForge")
        exit()
    return toml
