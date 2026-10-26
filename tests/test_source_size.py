"""No source file grows past the line limit; split a big module into a package instead."""

from __future__ import annotations

from pathlib import Path

LIMIT = 450
SRC = Path(__file__).resolve().parents[1] / "src"


def test_no_source_file_exceeds_the_line_limit() -> None:
    too_long = {
        str(path.relative_to(SRC)): count
        for path in sorted(SRC.rglob("*.py"))
        if (count := len(path.read_text(encoding="utf-8").splitlines())) > LIMIT
    }
    assert not too_long, f"source files above {LIMIT} lines: {too_long}"
