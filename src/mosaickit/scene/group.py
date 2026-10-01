from dataclasses import dataclass

from mosaickit.errors import ConfigurationError
from mosaickit.scene.layer import Layer


@dataclass(frozen=True, slots=True)
class GroupLayer(Layer):
    children: tuple[Layer, ...]

    def __post_init__(self) -> None:
        Layer.__post_init__(self)
        object.__setattr__(self, "children", tuple(self.children))
        if not all(isinstance(child, Layer) for child in self.children):
            raise ConfigurationError("Group children must be layers")
