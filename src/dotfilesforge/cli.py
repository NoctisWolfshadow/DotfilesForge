# src/main.py (refactored with click)


import click

from dotfilesforge import logger
from dotfilesforge.config import get_config, set_wsl
from dotfilesforge.dotfiles import Dotfiles
from dotfilesforge.package_manager import get_package_manager
from dotfilesforge.tools.factory import get_installers, install_dependencies


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
def install(ctx: click.Context, wsl: bool, remote_config: str | None = None):
    """Install dotfiles and tools"""
    logger.info("Installing dotfiles")
    _ = get_config(wsl, remote_config)
    _ = Dotfiles().check_and_install()
    installers = get_installers()
    _ = install_dependencies()
    for installer in installers:
        installer.check_and_install()


@cli.command()
@click.option("--wsl", is_flag=True, help="Exclude WSL-incompatible programs")
@click.pass_context
def update(ctx: click.Context, wsl: bool):
    """Install dotfiles and tools"""
    logger.info("Updating dotfiles")
    set_wsl(wsl)
    _ = Dotfiles().check_and_install()
    installers = get_installers()
    _ = get_package_manager().update_packages()
    for installer in installers:
        installer.check_and_install()


if __name__ == "__cli__":
    cli()
