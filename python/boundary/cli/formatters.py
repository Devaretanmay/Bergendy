import os
import sys


_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
def bold(text: str) -> str:
    return f"\x1b[1m{text}\x1b[0m" if _USE_COLOR else str(text)
def dim(text: str) -> str:
    return f"\x1b[2m{text}\x1b[0m" if _USE_COLOR else str(text)
def green(text: str) -> str:
    return f"\x1b[32;1m{text}\x1b[0m" if _USE_COLOR else str(text)
def red(text: str) -> str:
    return f"\x1b[31;1m{text}\x1b[0m" if _USE_COLOR else str(text)
def yellow(text: str) -> str:
    return f"\x1b[33m{text}\x1b[0m" if _USE_COLOR else str(text)
def cyan(text: str) -> str:
    return f"\x1b[36m{text}\x1b[0m" if _USE_COLOR else str(text)
def header(title: str) -> str:
    divider = "─" * 64
    return f"{bold(title)}\n{dim(divider)}"