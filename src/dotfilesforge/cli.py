# src/main.py (refactored with click)


import click

from dotfilesforge.config import get_config, set_wsl
from dotfilesforge.tools.factory import install_dependencies


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    pass


@cli.command()
@click.option("--wsl", is_flag=True, help="Exclude WSL-incompatible programs")
@click.option(
    "--remote-config",
    type=click.STRING,
    help="For Installs if you want DotfilesForge to install your Repo",
)
@click.pass_context
def install(ctx: click.Context, wsl: bool, remote_config: str | None):
    """Install dotfiles and tools"""
    print("Installing dotfiles")
    set_wsl(wsl)
    print(get_config())
    print(install_dependencies())


@cli.command()
@click.option("--wsl", is_flag=True, help="Exclude WSL-incompatible programs")
@click.pass_context
def update(ctx: click.Context, wsl: bool):
    """Install dotfiles and tools"""
    print("Installing dotfiles")


if __name__ == "__cli__":
    cli()
