from rich.console import Console

console = Console(force_terminal=True)


def info(text: str):
    console.print(text, style="bright_green")


def warn(text: str):
    console.print(text, style="orange")


def error(text: str):
    console.print(text, style="red bold")
