from enum import Enum


class ArrowStyle(str, Enum):
    OPEN = "open"
    TRIANGLE = "triangle"
    FANCY = "fancy"
    WEDGE = "wedge"


class ArrowPlacement(str, Enum):
    START = "start"
    END = "end"
    BOTH = "both"
