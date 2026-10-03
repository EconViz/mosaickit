from dataclasses import dataclass
from typing import ClassVar

import pytest

from mosaickit import (
    ConfigurationError,
    Fill,
    Stroke,
    StyleBundle,
    Theme,
    ThemeRegistry,
    expand_roles,
)
from mosaickit.themes.builtins import PRIMITIVE_DEFAULT


def test_role_resolution_merges_namespace_category_and_defaults():
    theme = Theme(
        "test",
        {
            "primary": StyleBundle(stroke=Stroke(width=4)),
            "mypkg": StyleBundle(stroke=Stroke(color="#123456")),
            "mypkg.boundary": StyleBundle(stroke=Stroke(width=2)),
            "mypkg.boundary.final": StyleBundle(stroke=Stroke(opacity=0)),
        },
    )
    style = theme.resolve("mypkg.boundary.final", fallback_category="primary")
    assert style.stroke.width == 2
    assert style.stroke.opacity == 0
    assert style.stroke.color.to_hex() == "#123456"
    assert style.fill == PRIMITIVE_DEFAULT.fill
    assert theme.resolve("new.package", fallback_category="primary").stroke.width == 4
    assert Theme("empty", {}).resolve("other", fallback_category="region") == PRIMITIVE_DEFAULT


def test_themes_copy_inputs_and_with_roles_merges():
    roles = {"a.b": StyleBundle(stroke=Stroke(width=4))}
    theme = Theme("test", roles)
    roles.clear()
    assert "a.b" in theme.roles
    with pytest.raises(TypeError):
        theme.roles["bad"] = StyleBundle()
    updated = theme.with_roles(**{"a.b": StyleBundle(stroke=Stroke(opacity=0))})
    assert updated.roles["a.b"].stroke.width == 4
    assert theme.roles["a.b"].stroke.opacity is None
    assert hash(theme) == hash(Theme("test", dict(theme.roles)))


def test_registry_rejects_undotted_domain_roles():
    registry = ThemeRegistry()
    with pytest.raises(ConfigurationError, match="dotted"):
        registry.register_roles("default", {"boundary": StyleBundle()})
    result = registry.register_roles(
        "default", {"mypkg.boundary": StyleBundle(fill=Fill(opacity=0))}
    )
    assert result.roles["mypkg.boundary"].fill.opacity == 0
    with pytest.raises(ConfigurationError):
        registry.register(result)
    with pytest.raises(ConfigurationError):
        registry.get("missing")


def test_role_pack_expansion():
    @dataclass(frozen=True)
    class Roles:
        _namespace: ClassVar[str] = "mypkg"
        boundary: StyleBundle = StyleBundle(stroke=Stroke(width=3))
        boundary_final: StyleBundle | None = None

    assert expand_roles(Roles()) == {"mypkg.boundary": StyleBundle(stroke=Stroke(width=3))}
