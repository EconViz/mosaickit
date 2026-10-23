"""Scene <-> JSON-compatible structure, version 1.

Every value that is not a plain number, string, boolean or ``None`` is written as an object
with a ``"$"`` tag naming its kind, so a loader never guesses a type. Sequences are lists.
Loading is strict: an unknown tag, an unknown or missing field, a non-finite number, a
document that is too large or too deeply nested, or a version this release does not know
raises ``ConfigurationError`` with the path to the offending value.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from mosaickit.colors import Color
from mosaickit.errors import ConfigurationError
from mosaickit.parameter import Constant, Parameter
from mosaickit.parameter.expression import Expression, _BinOp
from mosaickit.scene import (
    ArrowLayer,
    AxisLayer,
    AxisMarkLayer,
    AxisNoteLayer,
    AxisSpec,
    BraceLayer,
    FillLayer,
    GroupLayer,
    Layer,
    LegendLayer,
    MarkerLayer,
    PathLayer,
    PointLabelLayer,
    RegionLabelLayer,
    Scene,
    SpanBraceLayer,
    TextLayer,
)
from mosaickit.styles import (
    ArrowPlacement,
    ArrowStyle,
    DashStyle,
    Fill,
    LegendStyle,
    Marker,
    Nudge,
    Stroke,
    TextStyle,
)

FORMAT = "mosaickit.scene"
VERSION = 1

# Limits that let a consumer validate an untrusted document before building anything.
MAX_DEPTH = 64
MAX_NODES = 200_000
MAX_STRING = 10_000

_DATACLASSES: dict[str, type] = {
    cls.__name__: cls
    for cls in (
        ArrowLayer,
        AxisLayer,
        AxisMarkLayer,
        AxisNoteLayer,
        AxisSpec,
        BraceLayer,
        FillLayer,
        GroupLayer,
        LegendLayer,
        MarkerLayer,
        PathLayer,
        PointLabelLayer,
        RegionLabelLayer,
        SpanBraceLayer,
        TextLayer,
        Fill,
        LegendStyle,
        Marker,
        Nudge,
        Stroke,
        TextStyle,
    )
}
_ENUMS: dict[str, type[Enum]] = {
    cls.__name__: cls for cls in (ArrowPlacement, ArrowStyle, DashStyle)
}
_VALUE_TYPES: dict[str, type] = {"int": int, "float": float, "str": str, "bool": bool}
_NOT_SERIALIZED = frozenset({"model"})  # a layer's link back to the object that made it
# Fields added after version 1 shipped: left out while unset, so older documents stay the same.
_OMITTED_WHEN_NONE = frozenset({"nudge"})


class _Budget:
    """Counts the nodes visited so a hostile document cannot make loading unbounded."""

    def __init__(self) -> None:
        self.nodes = 0

    def spend(self, where: str) -> None:
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise ConfigurationError(f"{where}: document has more than {MAX_NODES} values")


def _fail(where: str, message: str) -> ConfigurationError:
    return ConfigurationError(f"{where}: {message}")


# --------------------------------------------------------------------------- writing


def _encode(value: Any, where: str, budget: _Budget, depth: int = 0) -> Any:
    budget.spend(where)
    if depth > MAX_DEPTH:
        raise _fail(where, f"nested more than {MAX_DEPTH} levels")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise _fail(where, f"text longer than {MAX_STRING} characters")
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _fail(where, "numbers must be finite")
        return value
    if isinstance(value, Enum):
        return {"$": type(value).__name__, "value": value.value}
    if isinstance(value, Color):
        return {"$": "Color", "channels": list(value.channels)}
    if isinstance(value, Parameter):
        kind = None
        if value.value_type is not None:
            kind = next((k for k, t in _VALUE_TYPES.items() if t is value.value_type), None)
            if kind is None:
                raise _fail(where, f"parameter type {value.value_type.__name__} is not supported")
        return {"$": "Parameter", "name": value.name, "value_type": kind}
    if isinstance(value, Constant):
        return {"$": "Constant", "value": _encode(value.value, where, budget, depth + 1)}
    if isinstance(value, _BinOp):
        return {
            "$": "BinOp",
            "operation": value.operation,
            "left": _encode(value.left, where, budget, depth + 1),
            "right": _encode(value.right, where, budget, depth + 1),
        }
    if is_dataclass(value) and not isinstance(value, type):
        name = type(value).__name__
        if _DATACLASSES.get(name) is not type(value):
            raise _fail(where, f"{name} cannot be serialized")
        out: dict[str, Any] = {"$": name}
        for slot in fields(value):
            if slot.name in _NOT_SERIALIZED or not slot.init:
                continue
            if slot.name in _OMITTED_WHEN_NONE and getattr(value, slot.name) is None:
                continue
            out[slot.name] = _encode(
                getattr(value, slot.name), f"{where}.{slot.name}", budget, depth + 1
            )
        return out
    if isinstance(value, Mapping):
        raise _fail(where, "a mapping cannot be serialized here")
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [_encode(item, f"{where}[{i}]", budget, depth + 1) for i, item in enumerate(value)]
    raise _fail(where, f"{type(value).__name__} cannot be serialized")


def scene_to_dict(scene: Scene) -> dict[str, Any]:
    """The scene as a JSON-compatible dict with a format name and version."""
    budget = _Budget()
    layers = [_encode(layer, f"layers[{i}]", budget) for i, layer in enumerate(scene.layers)]
    metadata = dict(scene.metadata)
    for key, text in metadata.items():
        if len(key) > MAX_STRING or len(text) > MAX_STRING:
            raise _fail("metadata", f"text longer than {MAX_STRING} characters")
    return {
        "format": FORMAT,
        "version": VERSION,
        "metadata": metadata,
        "layers": layers,
    }


def scene_to_json(scene: Scene, **options: Any) -> str:
    """The scene as JSON text; ``options`` go to ``json.dumps`` (``allow_nan`` stays off)."""
    options["allow_nan"] = False
    return json.dumps(scene_to_dict(scene), **options)


# --------------------------------------------------------------------------- reading


def _decode(value: Any, where: str, budget: _Budget, depth: int = 0) -> Any:
    budget.spend(where)
    if depth > MAX_DEPTH:
        raise _fail(where, f"nested more than {MAX_DEPTH} levels")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise _fail(where, f"text longer than {MAX_STRING} characters")
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _fail(where, "numbers must be finite")
        return value
    if isinstance(value, list):
        return tuple(
            _decode(item, f"{where}[{i}]", budget, depth + 1) for i, item in enumerate(value)
        )
    if not isinstance(value, dict):
        raise _fail(where, f"{type(value).__name__} is not a document value")
    tag = value.get("$")
    if not isinstance(tag, str):
        raise _fail(where, 'an object needs a "$" tag')
    body = {k: v for k, v in value.items() if k != "$"}

    def need(*names: str) -> None:
        unknown, missing = set(body) - set(names), set(names) - set(body)
        if unknown or missing:
            raise _fail(
                where,
                f"{tag} takes {sorted(names)}"
                + (f"; unknown {sorted(unknown)}" if unknown else "")
                + (f"; missing {sorted(missing)}" if missing else ""),
            )

    def child(name: str) -> Any:
        return _decode(body[name], f"{where}.{name}", budget, depth + 1)

    if tag in _ENUMS:
        need("value")
        try:
            return _ENUMS[tag](body["value"])
        except ValueError as exc:
            raise _fail(where, f"{body['value']!r} is not a {tag}") from exc
    if tag == "Color":
        need("channels")
        channels = child("channels")
        if not isinstance(channels, tuple) or len(channels) != 4:
            raise _fail(where, "Color.channels needs four numbers")
        return Color(*channels)
    if tag == "Parameter":
        need("name", "value_type")
        kind = body["value_type"]
        if kind is not None and kind not in _VALUE_TYPES:
            raise _fail(where, f"unknown parameter type {kind!r}")
        name = body["name"]
        if not isinstance(name, str):
            raise _fail(where, "Parameter.name must be text")
        return Parameter(name, None if kind is None else _VALUE_TYPES[kind])
    if tag == "Constant":
        need("value")
        return Constant(child("value"))
    if tag == "BinOp":
        need("operation", "left", "right")
        from mosaickit.parameter.expression import OPERATORS

        if body["operation"] not in OPERATORS:
            raise _fail(where, f"unknown operation {body['operation']!r}")
        left, right = child("left"), child("right")
        if not isinstance(left, Expression) or not isinstance(right, Expression):
            raise _fail(where, "BinOp operands must be expressions")
        return _BinOp(body["operation"], left, right)
    cls = _DATACLASSES.get(tag)
    if cls is None:
        raise _fail(where, f"unknown kind {tag!r}")
    if tag == "TextStyle" and "family" in body:
        # 0.9 wrote the removed field as null; a name is a font choice this release cannot honour
        if body["family"] is not None:
            raise _fail(where, "TextStyle.family was removed; use font and TextFonts")
        body = {name: value for name, value in body.items() if name != "family"}
    accepted = {s.name for s in fields(cls) if s.init and s.name not in _NOT_SERIALIZED}
    unknown = set(body) - accepted
    if unknown:
        raise _fail(where, f"{tag} has no fields {sorted(unknown)}")
    kwargs = {name: child(name) for name in body}
    try:
        return cls(**kwargs)
    except ConfigurationError as exc:
        raise _fail(where, str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise _fail(where, f"{tag}: {exc}") from exc


def scene_from_dict(document: Any) -> Scene:
    """Build the scene a ``scene_to_dict`` document describes; strict about everything else."""
    if not isinstance(document, dict):
        raise _fail("document", "must be an object")
    if document.get("format") != FORMAT:
        raise _fail("document", f"format must be {FORMAT!r}")
    version = document.get("version")
    if version != VERSION or isinstance(version, bool):
        raise _fail(
            "document", f"version {version!r} is not supported (this release reads {VERSION})"
        )
    unknown = set(document) - {"format", "version", "metadata", "layers"}
    if unknown:
        raise _fail("document", f"unknown keys {sorted(unknown)}")
    metadata = document.get("metadata", {})
    layers = document.get("layers", [])
    if not isinstance(metadata, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()
    ):
        raise _fail("metadata", "must map text to text")
    if not isinstance(layers, list):
        raise _fail("layers", "must be a list")
    budget = _Budget()
    decoded = tuple(_decode(layer, f"layers[{i}]", budget) for i, layer in enumerate(layers))
    for i, layer in enumerate(decoded):
        if not isinstance(layer, Layer):
            raise _fail(f"layers[{i}]", "is not a layer")
    try:
        return Scene(decoded, metadata)
    except ConfigurationError as exc:
        raise _fail("layers", str(exc)) from exc


def scene_from_json(text: str) -> Scene:
    """Build a scene from JSON text; invalid JSON and ``NaN`` are ``ConfigurationError``."""

    def reject(constant: str) -> Any:
        raise ConfigurationError(f"document: {constant} is not a finite number")

    try:
        document = json.loads(text, parse_constant=reject)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"document: not valid JSON ({exc})") from exc
    return scene_from_dict(document)
