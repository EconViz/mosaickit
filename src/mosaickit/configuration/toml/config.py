"""The class :meth:`Schema.config_class` makes: a built target plus its figure overrides."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from mosaickit.configuration import label_overrides
from mosaickit.configuration.label_overrides import FigureLabels
from mosaickit.configuration.toml.constants import FILE_NAME
from mosaickit.configuration.toml.figures import _NO_FIGURES, figure_labels
from mosaickit.configuration.toml.shared import find, read
from mosaickit.errors import ConfigurationError

if TYPE_CHECKING:
    from mosaickit.configuration.toml.schema import Schema


class ConfigBase:
    """Base of the classes :meth:`Schema.config_class` makes.

    ``config.value`` is the built target; other attributes are read from it, so
    ``config.theme`` works when the target has ``theme``.
    """

    __slots__ = ("figure_labels", "value")
    schema: ClassVar[Schema]
    _active: ClassVar[ConfigBase | None]

    def __init__(self, value: Any = None, *, figure_labels: FigureLabels | None = None) -> None:
        if value is None:
            value = self.schema.build({}, source="<defaults>")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "figure_labels", figure_labels)

    @classmethod
    def load(cls, path: str | Path | None = None) -> Any:
        """Read ``path``, or ``econ-viz.toml`` in the working directory (which must exist)."""
        file = Path(path) if path is not None else find()
        if file is None:
            raise ConfigurationError(f"config file not found: {FILE_NAME}")
        return cls._from_file(file)

    @classmethod
    def discover(cls, directory: str | Path | None = None) -> Any:
        """Read ``econ-viz.toml`` in ``directory`` if present, else the defaults."""
        file = find(directory)
        if file is None:
            return cls(cls.schema.build({}, source="<defaults>"), figure_labels=_NO_FIGURES)
        return cls._from_file(file)

    @classmethod
    def _from_file(cls, file: Path) -> Any:
        return cls.from_dict(read(file), source=str(file), base_dir=file.parent)

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        source: str = "<dict>",
        base_dir: str | Path | None = None,
    ) -> Any:
        """Build from already-parsed TOML data."""
        return cls(
            cls.schema.build(data, source=source, base_dir=base_dir),
            figure_labels=figure_labels(data, source=source),
        )

    def use(self) -> Any:
        """Make this the package's active config; returns ``self``.

        A config read from a file (``load``, ``discover``, ``from_dict``) also makes that
        file's ``[figure.*]`` label overrides the active ones (:func:`figure_overrides`),
        replacing those of any earlier activation, also when the file has none. A config
        made directly with ``Config(value)`` has no file and leaves them alone.
        """
        _owner(type(self))._active = self
        if self.figure_labels is not None:
            label_overrides.activate(self.figure_labels, _owner(type(self)))
        return self

    @classmethod
    def reset(cls) -> None:
        """Clear the package's active config, and the label overrides it activated."""
        owner = _owner(cls)
        owner._active = None
        if label_overrides.owned_by(owner):
            label_overrides.activate(None)

    @classmethod
    def active(cls) -> Any:
        """The package's active config, or ``None``."""
        return _owner(cls)._active

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") or name == "value":
            raise AttributeError(name)
        return getattr(object.__getattribute__(self, "value"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is read-only")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConfigBase) or _owner(type(other)) is not _owner(type(self)):
            return NotImplemented
        return bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash((_owner(type(self)), self.value))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.value!r})"


def _owner(cls: type) -> type[ConfigBase]:
    """The class config_class() made, which holds the active config for subclasses too."""
    for klass in cls.__mro__:
        if "schema" in klass.__dict__:
            return klass
    raise TypeError(f"{cls.__name__} was not made by Schema.config_class()")
