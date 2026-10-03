"""Gutter text as Matplotlib will draw it."""


def as_drawn(text: str, math: bool) -> str:
    return f"${text}$" if math and not (text.startswith("$") and text.endswith("$")) else text
