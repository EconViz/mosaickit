from enum import Enum


class Layout(str, Enum):
    SINGLE = "single"
    STACKED = "stacked"
    SIDE_BY_SIDE = "side_by_side"
    GRID_2X2 = "grid_2x2"
    GRID_3X3 = "grid_3x3"
    TOP_TWO_BOTTOM_ONE = "top_two_bottom_one"
    TOP_ONE_BOTTOM_TWO = "top_one_bottom_two"
