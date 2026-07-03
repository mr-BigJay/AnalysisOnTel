"""RTL-friendly Telegram HTML helpers for Persian reports."""

from __future__ import annotations

RLM = "\u200f"
LRM = "\u200e"


def rtl(text: str) -> str:
    """Force RTL paragraph direction."""
    if not text:
        return text
    if text.startswith(RLM):
        return text
    return f"{RLM}{text}"


def ltr(text: str) -> str:
    """Isolate LTR numbers and Latin text inside RTL."""
    return f"{LRM}{text}"


def divider(char: str = "─", width: int = 20) -> str:
    return char * width


def section(title: str, body: str | None = None) -> str:
    """Section with visual separators."""
    lines = [divider(), f"<b>{title}</b>", divider()]
    if body:
        lines.append(body.strip())
    return "\n".join(lines)


def row(label: str, value: str) -> str:
    """RTL table row: label ··· value."""
    return f"<b>{label}</b>  {value}"


def bullet(text: str) -> str:
    return f"▪️ {text}"


def wrap_message(text: str) -> str:
    """Wrap full Telegram HTML message for RTL."""
    return rtl(text.strip())
