# src/main.py (refactored with click)
from pathlib import Path

import click


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", type=click.Path(), help="Path to config file")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Path):
    pass


@cli.command()
@click.option("--wsl", is_flag=True, help="Exclude WSL-incompatible programs")
@click.pass_context
def install(ctx: click.Context, wsl: bool):
    """Install dotfiles and tools"""
    print("Installing dotfiles")


@cli.command()
@click.option("--wsl", is_flag=True, help="Exclude WSL-incompatible programs")
@click.pass_context
def update(ctx: click.Context, wsl: bool):
    """Install dotfiles and tools"""
    print("Installing dotfiles")


if __name__ == "__cli__":
    cli()
