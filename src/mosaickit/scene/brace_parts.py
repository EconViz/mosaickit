"""What every brace has besides where it sits: label styling, stroke, and checks."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from mosaickit.scene.layer import _text
from mosaickit.styles import Nudge, Stroke, TextStyle
from mosaickit.styles.nudge import check_nudge


@dataclass(frozen=True, kw_only=True)
class BraceParts:
    """Mixin for brace layers; list it first among the bases so its class settings
    win over ``Layer``'s. Subclasses declare ``label`` and ``side`` themselves
    (both may be passed positionally) and call ``_check_label`` after validation.
    ``nudge`` moves the placed label by a few points."""

    math: bool = False
    style: TextStyle | None = None
    stroke: Stroke | None = None
    nudge: Nudge | None = None
    fallback_category: ClassVar[str] = "text"
    style_slots: ClassVar[Mapping[str, str]] = {"stroke": "stroke", "text": "style"}

    def _check_label(self, owner: str) -> None:
        label = getattr(self, "label", None)
        if label is not None:
            _text(f"{owner}.label", label)
        check_nudge(owner, self.nudge)
