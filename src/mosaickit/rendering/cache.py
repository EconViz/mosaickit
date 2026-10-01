"""Bounded, thread-safe optional render cache."""

from __future__ import annotations

import warnings
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Any, TypeVar

from mosaickit.errors import ConfigurationError

T = TypeVar("T")


class CacheBypassWarning(UserWarning):
    """A model is not hashable; rendering continues without caching it."""


@dataclass(frozen=True, slots=True)
class CacheKey:
    layer_id: str
    bindings: Any
    model: Any
    viewport: Any
    tolerance: float
    theme_snapshot: Any


class RenderCache:
    def __init__(self, max_entries: int = 256) -> None:
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
            raise ConfigurationError("RenderCache.max_entries must be a positive integer")
        self.max_entries = max_entries
        self._entries: OrderedDict[CacheKey, Any] = OrderedDict()
        self._warned: set[type] = set()
        self._lock = RLock()

    def get_or_create(self, key: CacheKey, factory: Callable[[], T]) -> T:
        with self._lock:
            try:
                hash(key)
            except TypeError:
                model_type = type(key.model)
                if model_type not in self._warned:
                    warnings.warn(
                        f"Cache bypass for {model_type.__name__}; use a hashable model "
                        "(for example a frozen dataclass)",
                        CacheBypassWarning,
                        stacklevel=2,
                    )
                    self._warned.add(model_type)
                return factory()
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key]
            value = factory()
            self._entries[key] = value
            if len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
            return value

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
