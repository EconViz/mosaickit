from enum import Enum


class ArrowStyle(str, Enum):
    OPEN = "open"
    TRIANGLE = "triangle"
    FANCY = "fancy"
    WEDGE = "wedge"
    SIMPLE = "open"  # another name for OPEN

    @classmethod
    def _missing_(cls, value):
        """Also accept the Matplotlib spellings ``->`` (open) and ``-|>`` (triangle)."""
        return {"->": cls.OPEN, "-|>": cls.TRIANGLE}.get(value)


class ArrowPlacement(str, Enum):
    START = "start"
    END = "end"
    BOTH = "both"
