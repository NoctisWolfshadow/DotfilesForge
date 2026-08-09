
# DotfilesForge

## Mirror

Is Project is a mirror of my own hosted [Forgejo Instance](https://forgejo.noctiswolfshadow.com/NoctisWolfshadow/DotfilesForge).
If you have Problems or want to ask something please head to here.

## Disclaimer

This Project is still activly being developed. Breaking changes can occur often.
The first Release will be Stable but will not necessarily be without bugs.

## Description

This Python CLI Tool trys to deliver a always repeatable install of your Dotfiles
and the needed programs.
It is configured with a Toml Config File that is read in.
Tools to install can be also added if not yet in this Repository since all
Tools should follow the same Base Models.
If you add a Tool for yourself we would like if you also add a Pull Request so
it can be included for everyone else if possible.

## Installation

To install this package you can clone this Repository and use uv to run or
install it as tool.

Run this in the cloned Repository:

`uv run dotfilesforge [COMMAND]`
`uv tool install .`

## Config

This is how a config could look.

```toml
[paths]
git_repos = "~/git"
dotfiles = "~/.dotfiles"
appimages = "~/.dotfiles/AppImage"

[tools.ghostty]
enabled=true
version="tip"
#Optional defaults to true
wsl=false

[tools.neovim]
enabled=true
version="0.11.6"
install_method="default"

[services]
snap=true
flatpak=false
shell="zsh"

[packages]
pacman=['blueprint-compiler', 'ninja', 'gcc']

[dotfiles]
repo_name="test/test"
repo_host="custom" # github, gitlab
#Optional when not wanted https for cloning
#repo_modus="ssh"
#Only Used if repo_host is custom
repo_url="gitlab.noctiswolfshadow.com"

```
