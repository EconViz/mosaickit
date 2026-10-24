"""Schemas: packages declare their econ-viz.toml table and mosaickit builds the target."""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest
from matplotlib import get_data_path

from mosaickit import ConfigurationError, TextFonts, econ_toml
from mosaickit.econ_toml import (
    Context,
    Schema,
    boolean,
    choice,
    color,
    length,
    number,
    path,
    pattern,
    positive,
    string,
    transform,
)


@dataclass(frozen=True)
class Stroke:
    width: float = 1.0
    color: str = "#000000"


@dataclass(frozen=True)
class Colors:
    demand: str = "#111111"
    supply: str = "#222222"
    axis: str = "#333333"
    label: str = "#444444"


@dataclass(frozen=True)
class Theme:
    colors: Colors = field(default_factory=Colors)
    language: str = "en"
    width: float = 2.0
    ratio: float = 0.5
    grid: bool = False
    title: str = ""
    logo: str | None = None
    demand_stroke: Stroke = field(default_factory=Stroke)
    supply_stroke: Stroke = field(default_factory=Stroke)
    background: str = "#ffffff"
    font: str | None = None
    fonts: TextFonts | None = None
    math_font: str | None = None
    marker: float = 4.0


def _stroke(name: str, table: Mapping[str, Any], ctx: Context) -> Mapping[str, Any]:
    attr = f"{name}_stroke"
    if attr not in {"demand_stroke", "supply_stroke"}:
        raise ConfigurationError(f"no stroke named {name!r}")
    updates: dict[str, Any] = {}
    for key, value in table.items():
        if key == "width":
            updates[f"{attr}.width"] = positive("").convert(value, ctx, "width")
        elif key == "color":
            updates[f"{attr}.color"] = color("").convert(value, ctx, "color")
        else:
            raise ctx.error(f"unknown key {key!r}")
    return updates


def _area(value: Any, ctx: Context) -> float:
    if not isinstance(value, (int, float)) or value <= 0:
        raise ConfigurationError("must be a positive diameter")
    return float(value) ** 2


FIELDS = {
    "language": choice("language", ["en", "zh-TW"]),
    "width": positive("width"),
    "ratio": number("ratio", minimum=0, maximum=1),
    "grid": boolean("grid"),
    "title": string("title"),
    "logo": path("logo"),
    "marker": transform("marker", _area),
    "color.demand": color("colors.demand"),
    "color.supply": color("colors.supply"),
}


def make_schema(**overrides: Any) -> Schema:
    options: dict[str, Any] = {
        "package": "principle",
        "base": {"default": Theme, "dark": lambda: Theme(background="#000000")},
        "fields": FIELDS,
        "patterns": {"stroke": pattern("stroke", _stroke)},
        "shared": {
            "font": "font",
            "fonts": "fonts",
            "math_font": "math_font",
            "background": "background",
            "axis": "colors.axis",
            "label": "colors.label",
        },
        "docs": {"language": "Interface language.", "stroke": "Line width and colour."},
    }
    options.update(overrides)
    return Schema(**options)


SCHEMA = make_schema()


def build(data: Mapping[str, Any], schema: Schema = SCHEMA, **kwargs: Any) -> Any:
    return schema.build(data, **kwargs)


def error(data: Mapping[str, Any], schema: Schema = SCHEMA) -> str:
    with pytest.raises(ConfigurationError) as info:
        schema.build(data)
    return str(info.value)


# ---- field kinds


def test_empty_data_builds_the_default():
    assert build({}) == Theme()


def test_values_equal_to_the_default_give_the_default():
    data = {
        "principle": {
            "language": "en",
            "width": 2.0,
            "ratio": 0.5,
            "grid": False,
            "title": "",
            "color": {"demand": "#111111"},
            "stroke": {"demand": {"width": 1.0}},
        }
    }
    assert build(data) == Theme()


def test_every_field_kind_sets_its_attribute(tmp_path):
    data = {
        "principle": {
            "language": "zh-TW",
            "width": 3,
            "ratio": 1,
            "grid": True,
            "title": "Market",
            "logo": "img/logo.png",
            "marker": 3,
            "color": {"demand": "#8c8c8c", "supply": "tab:blue"},
        }
    }
    theme = build(data, base_dir=tmp_path)
    assert theme.language == "zh-TW"
    assert theme.width == 3
    assert theme.ratio == 1
    assert theme.grid is True
    assert theme.title == "Market"
    assert theme.logo == str(tmp_path / "img" / "logo.png")
    assert theme.marker == 9.0
    assert theme.colors == Colors(demand="#8c8c8c", supply="tab:blue")


@pytest.mark.parametrize(
    "value", ["#abc", "#AABBCC", "#aabbcc80", "black", "grey-900", "tab:red", "C0"]
)
def test_colour_values_accepted(value):
    assert build({"principle": {"color": {"demand": value}}}).colors.demand == value


@pytest.mark.parametrize("value", ["#abcd1", "#ggg", "#", "notacolour", "", 3, None])
def test_colour_values_rejected(value):
    message = error({"principle": {"color": {"demand": value}}})
    assert message.startswith("<dict>: [principle.color] demand must be a colour")


@pytest.mark.parametrize(
    ("key", "value", "problem"),
    [
        ("width", -1, "width must be a positive number, got -1"),
        ("width", 0, "width must be a positive number, got 0"),
        ("width", True, "width must be a positive number, got True"),
        ("width", "2", "width must be a positive number, got '2'"),
        ("width", float("nan"), "width must be a positive number, got nan"),
        ("ratio", 1.5, "ratio must be a number >= 0 and <= 1, got 1.5"),
        ("ratio", -0.1, "ratio must be a number >= 0 and <= 1, got -0.1"),
        ("grid", 1, "grid must be true or false, got 1"),
        ("title", 5, "title must be a string, got 5"),
        ("logo", 5, "logo must be a file path, got 5"),
        ("logo", "", "logo must be a file path, got ''"),
        ("language", "zh", "language must be one of 'en', 'zh-TW', got 'zh'"),
        ("marker", -2, "marker must be a positive diameter"),
    ],
)
def test_bad_field_values_name_the_table_and_key(key, value, problem):
    assert error({"principle": {key: value}}) == f"<dict>: [principle] {problem}"


def test_choice_suggests_a_close_option():
    assert error({"principle": {"language": "zh-tw"}}).endswith("did you mean 'zh-TW'?")


def test_number_bounds_and_exclusive_minimum():
    above = number("x", minimum=1, exclusive_minimum=True)
    ctx = Context("f", None, "[principle]")
    assert above.convert(1.5, ctx, "x") == 1.5
    with pytest.raises(ConfigurationError, match="x must be a number > 1, got 1"):
        above.convert(1, ctx, "x")
    assert number("x").convert(-5, ctx, "x") == -5
    with pytest.raises(ConfigurationError, match="x must be a number, got inf"):
        number("x").convert(float("inf"), ctx, "x")
    with pytest.raises(ConfigurationError, match="x must be a number <= 2"):
        number("x", maximum=2).convert(3, ctx, "x")


def test_choice_needs_string_options():
    with pytest.raises(ConfigurationError):
        choice("x", [])
    with pytest.raises(ConfigurationError):
        choice("x", [1, 2])  # type: ignore[list-item]


def test_transform_error_from_ctx_error_is_not_prefixed_twice():
    def convert(value: Any, ctx: Context) -> Any:
        raise ctx.error("bad thing")

    schema = make_schema(fields={"x": transform("title", convert)})
    assert error({"principle": {"x": 1}}, schema) == "<dict>: [principle] bad thing"


def test_transform_receives_the_context(tmp_path):
    seen = []

    def convert(value: Any, ctx: Context) -> Any:
        seen.append(ctx)
        return ctx.resolve(value)

    schema = make_schema(fields={"pic.file": transform("title", convert)})
    theme = schema.build(
        {"principle": {"pic": {"file": "a.png"}}}, source="s.toml", base_dir=tmp_path
    )
    assert theme.title == str(tmp_path / "a.png")
    assert seen[0] == Context("s.toml", tmp_path, "[principle.pic]")


# ---- dotted attrs


@dataclass(frozen=True)
class Inner:
    a: int = 0
    b: int = 0


@dataclass(frozen=True)
class Middle:
    inner: Inner = field(default_factory=Inner)
    c: int = 0


@dataclass(frozen=True)
class Outer:
    middle: Middle = field(default_factory=Middle)
    d: int = 0


def test_dotted_attrs_rebuild_each_nested_object_once(monkeypatch):
    calls: list[type] = []
    import mosaickit.econ_toml as module

    real = module.replace

    def counting(obj: Any, **changes: Any) -> Any:
        calls.append(type(obj))
        return real(obj, **changes)

    monkeypatch.setattr(module, "replace", counting)
    schema = Schema(
        "macro",
        {"default": Outer},
        fields={
            "a": number("middle.inner.a"),
            "b": number("middle.inner.b"),
            "c": number("middle.c"),
            "d": number("d"),
        },
    )
    assert schema.build({"macro": {"a": 1, "b": 2, "c": 3, "d": 4}}) == Outer(
        Middle(Inner(1, 2), 3), 4
    )
    assert sorted(calls, key=lambda t: t.__name__) == [Inner, Middle, Outer]


def test_a_whole_value_then_nested_values_apply_in_order():
    schema = Schema(
        "macro",
        {"default": Outer},
        fields={
            "inner": transform("middle.inner", lambda v, ctx: Inner(v, v)),
            "a": number("middle.inner.a"),
        },
    )
    assert schema.build({"macro": {"inner": 5, "a": 1}}).middle.inner == Inner(1, 5)
    # A later whole value replaces earlier nested ones.
    assert schema.build({"macro": {"a": 1, "inner": 5}}).middle.inner == Inner(5, 5)


def test_unknown_or_non_dataclass_attrs_are_reported():
    bad = Schema("macro", {"default": Outer}, fields={"x": number("middle.nope")})
    with pytest.raises(ConfigurationError, match="no attribute 'middle.nope'"):
        bad.build({"macro": {"x": 1}})
    deep = Schema("macro", {"default": Outer}, fields={"x": number("d.real")})
    with pytest.raises(ConfigurationError, match="not a dataclass"):
        deep.build({"macro": {"x": 1}})


# ---- base


def test_base_selects_a_built_in_target():
    assert build({"base": "dark"}).background == "#000000"
    assert build({"base": "default"}) == Theme()


def test_unknown_base_lists_this_packages_names():
    message = error({"base": "drak"})
    assert message == (
        "<dict>: base 'drak' is not a built-in principle theme; choose from dark, default; "
        "did you mean 'dark'?"
    )
    assert "must be a string" in error({"base": 3})


def test_schema_definition_is_checked():
    with pytest.raises(ConfigurationError, match="must contain 'default'"):
        make_schema(base={"dark": Theme})
    with pytest.raises(ConfigurationError, match="unknown package 'econ'"):
        make_schema(package="econ")
    with pytest.raises(ConfigurationError, match="unknown shared setting"):
        make_schema(shared={"colour": "background"})
    with pytest.raises(ConfigurationError, match="pattern key"):
        make_schema(patterns={"line": pattern("stroke", _stroke)})
    with pytest.raises(ConfigurationError, match="bad field key"):
        make_schema(fields={"a..b": number("width")})
    with pytest.raises(ConfigurationError, match="dotted name"):
        pattern("", _stroke)


@pytest.mark.parametrize("package", sorted(econ_toml.PACKAGES))
def test_every_reserved_package_name_is_a_valid_schema(package):
    assert make_schema(package=package).package == package


# ---- shared settings


def test_shared_settings_map_onto_the_target(tmp_path):
    (tmp_path / "fonts").mkdir()
    font = Path(get_data_path()) / "fonts" / "ttf" / "DejaVuSerif.ttf"
    (tmp_path / "fonts" / "a.otf").write_bytes(font.read_bytes())
    data = {
        "font": {"text": "serif", "math": "fonts/math.otf"},
        "fonts": {"serif": "fonts/a.otf"},
        "color": {"background": "#fafafa", "axis": "#010101", "label": "black"},
    }
    theme = build(data, base_dir=tmp_path)
    assert theme.font == "serif"
    assert theme.math_font == str(tmp_path / "fonts" / "math.otf")
    assert theme.fonts == TextFonts(serif=(tmp_path / "fonts" / "a.otf",))
    assert theme.background == "#fafafa"
    assert theme.colors.axis == "#010101"
    assert theme.colors.label == "black"


def test_unmapped_shared_settings_are_ignored():
    schema = make_schema(shared={"background": "background"})
    theme = schema.build({"font": {"text": "mono"}, "color": {"axis": "#010101"}})
    assert theme == Theme()


def test_shared_mapping_can_be_a_field():
    schema = make_schema(shared={"math_font": transform("title", lambda v, ctx: f"<{v}>")})
    theme = schema.build({"font": {"math": "/m.otf"}})
    assert theme.title == "</m.otf>"


def test_bad_shared_values():
    assert error({"color": {"axis": "nope"}}) == "<dict>: [color] axis must be a colour, got 'nope'"
    assert "[font] text must be one of" in error({"font": {"text": "fantasy"}})
    assert error({"font": {"txet": "serif"}}) == (
        "<dict>: [font] unknown key 'txet'; did you mean 'text'?"
    )
    assert "[font] must be a table" in error({"font": "serif"})


def test_package_tables_win_over_shared_values():
    data = {"color": {"axis": "#010101"}, "principle": {"color": {"demand": "#020202"}}}
    assert build(data).colors == Colors(demand="#020202", axis="#010101")


# ---- unknown keys


def test_unknown_key_in_a_package_table_suggests_a_close_one():
    message = error({"principle": {"color": {"demnad": "#000000"}}})
    assert message == "<dict>: [principle.color] unknown key 'demnad'; did you mean 'demand'?"


def test_unknown_key_without_a_close_match_lists_the_valid_keys():
    assert error({"principle": {"zzz": 1}}) == (
        "<dict>: [principle] unknown key 'zzz'; choose from color, grid, language, logo, "
        "marker, ratio, stroke, title, width"
    )
    assert error({"principle": {"color": {"zzz": "#000"}}}) == (
        "<dict>: [principle.color] unknown key 'zzz'; choose from demand, supply"
    )
    assert error({"fonts": {"zzz": "a.otf"}}) == (
        "<dict>: [fonts] unknown key 'zzz'; choose from mono, sans, serif"
    )
    assert error({"fonts": {"sanss": "a.otf"}}) == (
        "<dict>: [fonts] unknown key 'sanss'; did you mean 'sans'?"
    )
    assert error({"zzz": 1}).startswith(
        "<dict>: unknown top-level key 'zzz'; choose from base, color, dsge, figure, font, fonts,"
    )


def test_font_file_errors_name_the_source_and_table(tmp_path):
    with pytest.raises(ConfigurationError) as info:
        SCHEMA.build({"fonts": {"sans": []}}, source="econ-viz.toml")
    assert str(info.value) == "econ-viz.toml: [fonts] sans needs at least one font file"
    with pytest.raises(ConfigurationError) as info:
        SCHEMA.build({"fonts": {"serif": "missing.otf"}}, source="s.toml", base_dir=tmp_path)
    assert str(info.value).startswith("s.toml: [fonts] serif ")
    assert "TextFonts" not in str(info.value)


def test_unknown_top_level_key_suggests_a_close_one():
    assert error({"colour": {}}) == "<dict>: unknown top-level key 'colour'; did you mean 'color'?"
    assert error({"principal": {}}).endswith("did you mean 'principle'?")


def test_sections_and_patterns_must_be_tables():
    assert error({"principle": {"color": "red"}}) == "<dict>: [principle] color must be a table"
    assert error({"principle": {"stroke": 3}}) == "<dict>: [principle] stroke must be a table"
    assert error({"principle": 3}) == "<dict>: [principle] must be a table"
    assert error({"principle": {"stroke": {"demand": 3}}}) == (
        "<dict>: [principle.stroke] demand must be a table"
    )


def test_other_packages_tables_are_ignored():
    data = {
        "utility": {"anything": {"at": "all"}},
        "micro": 3,
        "macro": {"color": {"x": 1}},
        "game": [],
    }
    assert build(data) == Theme()


def test_legacy_utility_layout_is_ignored_by_other_packages():
    data = {"stroke": {"ic": {"width": 2}}, "legend": {}, "color": {"ic": "#8c8c8c"}}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert build(data) == Theme()


# ---- patterns


def test_patterns_match_any_name_and_set_attrs():
    data = {"principle": {"stroke": {"demand": {"width": 3.5}, "supply": {"color": "#123456"}}}}
    theme = build(data)
    assert theme.demand_stroke == Stroke(width=3.5)
    assert theme.supply_stroke == Stroke(color="#123456")


def test_pattern_errors_are_prefixed_with_their_table():
    assert error({"principle": {"stroke": {"demand": {"width": -1}}}}) == (
        "<dict>: [principle.stroke.demand] width must be a positive number, got -1"
    )
    assert error({"principle": {"stroke": {"tax": {"width": 1}}}}) == (
        "<dict>: [principle.stroke.tax] no stroke named 'tax'"
    )
    assert error({"principle": {"stroke": {"demand": {"wdth": 1}}}}) == (
        "<dict>: [principle.stroke.demand] unknown key 'wdth'"
    )


def test_dotted_pattern_prefix():
    schema = make_schema(patterns={"style.stroke": pattern("style.stroke", _stroke)})
    theme = schema.build({"principle": {"style": {"stroke": {"demand": {"width": 2}}}}})
    assert theme.demand_stroke.width == 2


# ---- legacy top level


def legacy_schema(**overrides: Any) -> Schema:
    messages: list[str] = []
    schema = make_schema(
        package="utility",
        legacy_top_level=True,
        legacy_warning=messages.append,
        **overrides,
    )
    return schema, messages  # type: ignore[return-value]


def test_legacy_top_level_keys_move_under_the_package_with_one_warning():
    schema, messages = legacy_schema()
    data = {
        "color": {"demand": "#010101", "axis": "#020202"},
        "stroke": {"demand": {"width": 3}},
        "width": 5,
    }
    theme = schema.build(data, source="econ-viz.toml")
    assert theme.colors == Colors(demand="#010101", axis="#020202")
    assert theme.demand_stroke.width == 3
    assert theme.width == 5
    assert len(messages) == 1
    assert messages[0].startswith("econ-viz.toml: utility settings at the top level are deprecated")
    assert "[color] demand -> [utility.color] demand" in messages[0]
    assert "[stroke] -> [utility.stroke]" in messages[0]


def test_package_table_wins_over_legacy_keys_and_still_warns():
    schema, messages = legacy_schema()
    data = {
        "color": {"demand": "#010101", "supply": "#030303"},
        "stroke": {"demand": {"width": 3, "color": "#040404"}},
        "utility": {"color": {"demand": "#020202"}, "stroke": {"demand": {"width": 4}}},
    }
    theme = schema.build(data)
    assert theme.colors.demand == "#020202"
    assert theme.colors.supply == "#030303"
    assert theme.demand_stroke == Stroke(width=4, color="#040404")
    assert len(messages) == 1


def test_new_layout_does_not_warn():
    schema, messages = legacy_schema()
    assert schema.build({"utility": {"color": {"demand": "#020202"}}}).colors.demand == "#020202"
    assert messages == []


def test_legacy_typos_are_still_reported():
    schema, _ = legacy_schema()
    assert error({"color": {"demnad": "#000000"}}, schema) == (
        "<dict>: [color] unknown key 'demnad'; did you mean 'demand'?"
    )
    assert error({"strok": {}}, schema) == (
        "<dict>: unknown top-level key 'strok'; did you mean 'stroke'?"
    )


def test_legacy_warning_defaults_to_future_warning():
    schema = make_schema(package="utility", legacy_top_level=True)
    with pytest.warns(FutureWarning, match=r"\[stroke\] -> \[utility.stroke\]"):
        schema.build({"stroke": {"demand": {"width": 2}}})


# ---- paths


def test_relative_paths_resolve_against_the_file_directory(tmp_path, monkeypatch):
    (tmp_path / "conf").mkdir()
    file = tmp_path / "conf" / econ_toml.FILE_NAME
    file.write_text('[font]\nmath = "m.otf"\n[principle]\nlogo = "../logo.png"\n', "utf-8")
    monkeypatch.chdir(tmp_path)
    theme = SCHEMA.load(Path("conf") / econ_toml.FILE_NAME)
    assert Path(theme.math_font).is_absolute()
    assert Path(theme.math_font) == tmp_path / "conf" / "m.otf"
    assert Path(theme.logo) == tmp_path / "conf" / ".." / "logo.png"


def test_absolute_and_home_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    theme = build({"principle": {"logo": "~/x.png"}}, base_dir="/elsewhere")
    assert theme.logo == str(tmp_path / "x.png")
    theme = build({"principle": {"logo": "/abs/x.png"}}, base_dir=tmp_path)
    assert theme.logo == "/abs/x.png"


def test_dict_paths_without_base_dir_resolve_against_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert build({"principle": {"logo": "x.png"}}).logo == str(tmp_path / "x.png")


# ---- load, discover, finalize


def test_load_and_discover(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigurationError, match="config file not found: econ-viz.toml"):
        SCHEMA.load()
    assert SCHEMA.discover() == Theme()
    assert SCHEMA.discover(tmp_path / "missing") == Theme()
    (tmp_path / econ_toml.FILE_NAME).write_text('[principle]\ntitle = "x"\n', "utf-8")
    assert SCHEMA.load().title == "x"
    assert SCHEMA.discover().title == "x"
    assert SCHEMA.discover(tmp_path).title == "x"
    with pytest.raises(ConfigurationError, match="config file not found"):
        SCHEMA.load(tmp_path / "nope.toml")


def test_load_errors_name_the_file(tmp_path):
    file = tmp_path / econ_toml.FILE_NAME
    file.write_text('[principle.color]\ndemnad = "#000"\n', "utf-8")
    with pytest.raises(ConfigurationError) as info:
        SCHEMA.load(file)
    assert str(info.value) == (
        f"{file}: [principle.color] unknown key 'demnad'; did you mean 'demand'?"
    )


def test_finalize_runs_last():
    seen = []

    def finalize(theme: Theme, ctx: Context) -> Theme:
        seen.append(ctx)
        return replace(theme, title=theme.title + "!")

    schema = make_schema(finalize=finalize)
    assert schema.build({"principle": {"title": "a"}}, source="s").title == "a!"
    assert seen == [Context("s", None, "")]


def test_context_error_and_resolve(tmp_path):
    ctx = Context("f.toml", tmp_path, "[principle]")
    assert str(ctx.error("x is bad")) == "f.toml: [principle] x is bad"
    assert isinstance(ctx.error("x"), ConfigurationError)
    assert str(Context("f.toml", None, "").error("bad")) == "f.toml: bad"
    assert ctx.resolve("a/b") == str(tmp_path / "a" / "b")


# ---- config_class


@pytest.fixture
def Config():  # noqa: N802 - it is a class
    cls = SCHEMA.config_class()
    yield cls
    cls.reset()


def test_config_class_builds_and_passes_attributes_through(Config, tmp_path):
    config = Config.from_dict({"principle": {"title": "t"}}, source="s", base_dir=tmp_path)
    assert config.value == Theme(title="t")
    assert config.title == "t"
    assert config.colors == Colors()
    assert Config.__name__ == "Config"
    assert SCHEMA.config_class("PrincipleConfig").__name__ == "PrincipleConfig"
    with pytest.raises(AttributeError):
        config.nope  # noqa: B018
    with pytest.raises(AttributeError):
        config.title = "x"
    assert Config() == Config(Theme())
    assert Config.from_dict({}) == Config()
    assert hash(Config()) == hash(Config())
    assert repr(Config()).startswith("Config(Theme(")


def test_config_load_and_discover(Config, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Config.discover().value == Theme()
    with pytest.raises(ConfigurationError):
        Config.load()
    (tmp_path / econ_toml.FILE_NAME).write_text("[principle]\nwidth = 4\n", "utf-8")
    assert Config.load().width == 4
    assert Config.load(tmp_path / econ_toml.FILE_NAME).width == 4
    assert Config.discover(tmp_path).width == 4


def test_use_reset_active(Config):
    assert Config.active() is None
    config = Config.from_dict({"principle": {"width": 9}})
    assert config.use() is config
    assert Config.active() is config
    Config.reset()
    assert Config.active() is None


def test_each_config_class_has_its_own_active_config():
    first, second = SCHEMA.config_class(), SCHEMA.config_class()
    first().use()
    assert second.active() is None
    first.reset()


def test_subclasses_add_properties_and_share_the_active_config(Config):
    class PrincipleConfig(Config):
        @property
        def theme(self) -> Theme:
            return self.value

    config = PrincipleConfig.from_dict({"principle": {"width": 3}})
    assert isinstance(config, PrincipleConfig)
    assert config.theme.width == 3
    assert config.width == 3
    config.use()
    assert Config.active() is config
    assert PrincipleConfig.active() is config
    PrincipleConfig.reset()
    assert Config.active() is None
    assert PrincipleConfig.discover("/nonexistent").theme == Theme()


def test_configs_of_different_schemas_are_not_equal():
    other = make_schema(package="macro").config_class()
    assert SCHEMA.config_class()() != other()


def test_config_base_needs_a_schema():
    with pytest.raises(TypeError):
        econ_toml.ConfigBase.reset()


# ---- template


def test_template_lists_every_key_with_its_default():
    text = SCHEMA.template()
    assert text == (
        "# [principle]\n"
        '# language = "en"  # Interface language.\n'
        "# width = 2.0\n"
        "# ratio = 0.5\n"
        "# grid = false\n"
        '# title = ""\n'
        "# logo = ...  # (no default)\n"
        "# marker = 4.0\n"
        "\n"
        "# [principle.color]\n"
        '# demand = "#111111"\n'
        '# supply = "#222222"\n'
        "\n"
        "# [principle.stroke.<name>]\n"
        "# Line width and colour.\n"
    )


def test_template_is_valid_toml_once_uncommented():
    head = SCHEMA.template().split("# [principle.stroke")[0]
    lines = [line[2:] for line in head.splitlines() if "= ..." not in line]
    data = econ_toml.tomllib.loads("\n".join(lines))
    # marker is a transform (diameter -> area), so its default does not round-trip.
    assert replace(SCHEMA.build(data), marker=4.0) == Theme()


def test_template_shows_no_invented_colour_for_a_missing_default():
    @dataclass(frozen=True)
    class Bare:
        ic: str | None = None

    schema = Schema(
        "utility", {"default": Bare}, fields={"color.ic": color("ic")}, docs={"color.ic": "IC."}
    )
    assert schema.template() == "# [utility.color]\n# ic = ...  # IC. (no default)\n"


def test_template_of_an_empty_schema_and_odd_defaults():
    @dataclass(frozen=True)
    class Odd:
        colour: Any = None
        sizes: tuple[int, ...] = (1, 2)
        when: Any = float("nan")

    from mosaickit.colors import Color  # noqa: PLC0415

    schema = Schema(
        "game",
        {"default": lambda: Odd(colour=Color.from_hex("#ABCDEF"))},
        fields={
            "colour": color("colour"),
            "sizes": transform("sizes", lambda v, ctx: v),
            "when": transform("when", lambda v, ctx: v),
        },
    )
    assert schema.template() == ('# [game]\n# colour = "#ABCDEF"\n# sizes = [1, 2]\n# when = ...\n')
    assert Schema("game", {"default": Odd}).template() == "# [game]\n"


# ---- registry and entry points


@pytest.fixture
def clean_registry(monkeypatch):
    monkeypatch.setattr(econ_toml, "_REGISTRY", {})


def test_register_and_registered(clean_registry):
    assert econ_toml.registered() == {}
    first = econ_toml.register(SCHEMA)
    assert first is SCHEMA
    replacement = econ_toml.register(make_schema())
    macro = econ_toml.register(make_schema(package="macro"))
    assert dict(econ_toml.registered()) == {"principle": replacement, "macro": macro}
    with pytest.raises(TypeError):
        econ_toml.registered()["x"] = SCHEMA  # type: ignore[index]


def test_load_builds_every_registered_package(clean_registry, tmp_path, monkeypatch):
    econ_toml.register(SCHEMA)
    econ_toml.register(make_schema(package="macro"))
    file = tmp_path / econ_toml.FILE_NAME
    file.write_text('base = "dark"\n[principle]\nwidth = 3\n[macro]\nwidth = 4\n', "utf-8")
    built = econ_toml.load(file)
    assert built["principle"] == Theme(width=3, background="#000000")
    assert built["macro"] == Theme(width=4, background="#000000")
    monkeypatch.chdir(tmp_path)
    assert econ_toml.load()["macro"].width == 4
    (tmp_path / "empty").mkdir()
    monkeypatch.chdir(tmp_path / "empty")
    with pytest.raises(ConfigurationError, match="config file not found"):
        econ_toml.load()


class _EntryPoint:
    def __init__(self, target: Any) -> None:
        self.target = target

    def load(self) -> Any:
        return self.target


def test_use_activates_every_installed_package(tmp_path, monkeypatch):
    principle = SCHEMA.config_class()
    macro = make_schema(package="macro").config_class()
    groups: list[str] = []

    def entry_points(*, group: str) -> list[_EntryPoint]:
        groups.append(group)
        return [_EntryPoint(principle), _EntryPoint(macro)]

    monkeypatch.setattr(econ_toml.metadata, "entry_points", entry_points)
    file = tmp_path / econ_toml.FILE_NAME
    file.write_text("[principle]\nwidth = 3\n[macro]\nwidth = 4\n", "utf-8")
    try:
        assert econ_toml.use(file) is None
        assert groups == ["econviz.config"]
        assert principle.active().width == 3
        assert macro.active().width == 4
        monkeypatch.chdir(tmp_path)
        econ_toml.use()
        assert principle.active().width == 3
    finally:
        principle.reset()
        macro.reset()


def test_use_without_installed_packages_does_nothing(monkeypatch):
    monkeypatch.setattr(econ_toml.metadata, "entry_points", lambda *, group: [])
    econ_toml.use("/does/not/matter.toml")


# ---- length


@pytest.mark.parametrize(
    ("value", "points"),
    [
        (3, 3.0),
        (2.5, 2.5),
        (-1, -1.0),
        ("10pt", 10.0),
        ("-3pt", -3.0),
        ("+1.5pt", 1.5),
        (" 4 pt ", 4.0),
        (".5pt", 0.5),
        ("0.1in", 7.2),
        ("1in", 72.0),
        ("25.4mm", 72.0),
        ("2mm", 2 * 72 / 25.4),
        ("2.54cm", 72.0),
    ],
)
def test_length_returns_points(value, points):
    schema = make_schema(fields={"gap": length("width")})
    assert schema.build({"principle": {"gap": value}}).width == pytest.approx(points)


@pytest.mark.parametrize(
    "value", ["10", "10px", "pt", "1.2.3pt", "", True, None, float("nan"), [1]]
)
def test_length_rejects_other_values(value):
    schema = make_schema(fields={"gap": length("width")})
    assert error({"principle": {"gap": value}}, schema).startswith(
        "<dict>: [principle] gap must be a length "
        "(a number of points or a string in pt, mm, cm, in)"
    )


def test_length_rejects_em():
    schema = make_schema(fields={"gap": length("width")})
    assert error({"principle": {"gap": "1.5em"}}, schema) == (
        "<dict>: [principle] gap cannot be in em here (no font size); use pt, mm, cm, in"
    )
