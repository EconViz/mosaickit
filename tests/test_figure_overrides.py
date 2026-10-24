"""Per-figure label overrides: ``[figure.<stem>.label."<id>"]`` in econ-viz.toml."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import pytest

from mosaickit import (
    BraceLayer,
    Canvas,
    CanvasGrid,
    ConfigurationError,
    Fill,
    FillLayer,
    GroupLayer,
    MarkerLayer,
    Nudge,
    PathLayer,
    PointLabelLayer,
    RegionLabelLayer,
    SpanBraceLayer,
    TextLayer,
    econ_toml,
)
from mosaickit.econ_toml import Schema, figure_labels, figure_overrides
from mosaickit.scene import Scene
from mosaickit.scene.label_nudges import with_label_nudges

pytestmark = pytest.mark.filterwarnings("ignore::mosaickit.errors.LayoutWarning")

TOML = """
[figure.tax_welfare.label."market.welfare.dwl.label"]
top = "12pt"
right = "8pt"

[figure.tax_welfare.label.plain]
left = 3
bottom = "1mm"

[figure."fig.v2".label."dot.label"]
top = 5
"""


@dataclass(frozen=True)
class Theme:
    title: str = ""


CONFIG = Schema(package="principle", base={"default": Theme}).config_class("Config")


@pytest.fixture(autouse=True)
def clean():
    econ_toml.clear_figure_overrides()
    yield
    econ_toml.clear_figure_overrides()
    CONFIG.reset()


def parse(text: str) -> Any:
    return figure_labels(econ_toml.tomllib.loads(text), source="econ-viz.toml")


def error(text: str) -> str:
    with pytest.raises(ConfigurationError) as caught:
        parse(text)
    return str(caught.value)


# ---- parsing


def test_parses_stems_ids_and_sides_into_nudges():
    figures = parse(TOML)
    assert set(figures) == {"tax_welfare", "fig.v2"}
    nudges = figures["tax_welfare"]
    assert nudges["market.welfare.dwl.label"] == Nudge(dx=8, dy=12)
    assert nudges["plain"] == Nudge(dx=-3, dy=-72 / 25.4)  # 1 mm down
    assert figures["fig.v2"]["dot.label"] == Nudge(dx=0, dy=5)


def test_opposite_sides_combine_and_an_empty_table_is_a_zero_nudge():
    figures = parse(
        "[figure.a.label.x]\ntop = 10\nbottom = 4\nleft = 1\nright = 2.5\n[figure.a.label.y]\n"
    )
    assert figures["a"]["x"] == Nudge(dx=1.5, dy=6)
    assert figures["a"]["y"].is_zero


def test_no_figure_table_means_no_overrides():
    assert figure_labels({}) == {}
    assert econ_toml.shared_settings({}).figures == {}


def test_overrides_are_read_only():
    figures = parse(TOML)
    with pytest.raises(TypeError):
        figures["x"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        figures["tax_welfare"]["x"] = Nudge()  # type: ignore[index]


def test_shared_settings_carry_the_overrides():
    shared = econ_toml.shared_settings(econ_toml.tomllib.loads(TOML))
    assert shared.figures == parse(TOML)


@pytest.mark.parametrize(
    "text,message",
    [
        ("figure = 1", "econ-viz.toml: [figure] must be a table"),
        ("[figure]\na = 1", "econ-viz.toml: [figure.a] must be a table"),
        (
            "[figure.a]\nlabels = {}",
            "econ-viz.toml: [figure.a] unknown key 'labels'; did you mean 'label'?",
        ),
        ("[figure.a]\nlabel = 1", "econ-viz.toml: [figure.a] label must be a table"),
        ("[figure.a.label]\nx = 1", "econ-viz.toml: [figure.a.label] 'x' must be a table"),
        (
            "[figure.a.label.x]\ntopp = 1",
            "econ-viz.toml: [figure.a.label.x] unknown key 'topp'; did you mean 'top'?",
        ),
        (
            '[figure.a.label."x.y"]\nzzz = 1',
            "econ-viz.toml: [figure.a.label.\"x.y\"] unknown key 'zzz'; "
            "choose from bottom, left, right, top",
        ),
        (
            '[figure."a.b".label.x]\ntop = "1em"',
            'econ-viz.toml: [figure."a.b".label.x] top cannot be in em here (no font size);',
        ),
        (
            "[figure.a.label.x]\ntop = true",
            "econ-viz.toml: [figure.a.label.x] top must be a length",
        ),
        (
            '[figure.a.label.x]\nright = "ten"',
            "econ-viz.toml: [figure.a.label.x] right must be a length",
        ),
        (
            "[figure.a.label.x]\nleft = [1]",
            "econ-viz.toml: [figure.a.label.x] left must be a length",
        ),
    ],
)
def test_malformed_overrides_name_the_file_and_table(text, message):
    assert error(text).startswith(message)


def test_the_figure_table_is_not_an_unknown_top_level_key(tmp_path):
    data = {"figure": {"a": {"label": {"x": {"top": 1}}}}}
    for package in sorted(econ_toml.PACKAGES):
        schema = Schema(package=package, base={"default": Theme})
        assert schema.build(data) == Theme()
    legacy = Schema(package="utility", base={"default": Theme}, legacy_top_level=True)
    assert legacy.build(data) == Theme()
    assert "figure" in econ_toml.SHARED_SECTIONS


def test_building_a_package_reports_bad_overrides():
    schema = Schema(package="principle", base={"default": Theme})
    with pytest.raises(ConfigurationError, match=r"<dict>: \[figure.a.label.x\] top must be"):
        schema.build({"figure": {"a": {"label": {"x": {"top": "no"}}}}})


# ---- activation


def write(tmp_path: Path, text: str = TOML) -> Path:
    path = tmp_path / econ_toml.FILE_NAME
    path.write_text(text, encoding="utf-8")
    return path


def test_nothing_is_active_by_default():
    assert figure_overrides() == {}
    assert figure_overrides("tax_welfare") == {}


def test_use_activates_the_files_overrides(tmp_path):
    config = CONFIG.load(write(tmp_path))
    assert config.figure_labels == parse(TOML)
    assert figure_overrides() == {}  # loading alone activates nothing
    config.use()
    assert figure_overrides() == parse(TOML)
    assert figure_overrides("fig.v2") == {"dot.label": Nudge(dy=5)}
    assert figure_overrides("other") == {}


def test_discover_and_from_dict_carry_the_overrides(tmp_path):
    write(tmp_path)
    CONFIG.discover(tmp_path).use()
    assert set(figure_overrides()) == {"tax_welfare", "fig.v2"}
    CONFIG.discover(tmp_path / "nowhere").use()
    assert figure_overrides() == {}
    CONFIG.from_dict({"figure": {"a": {"label": {"x": {"top": 1}}}}}).use()
    assert figure_overrides("a") == {"x": Nudge(dy=1)}


def test_the_last_activated_config_wins_and_a_direct_config_keeps_them(tmp_path):
    CONFIG.load(write(tmp_path)).use()
    CONFIG(Theme("direct")).use()
    assert "tax_welfare" in figure_overrides()
    CONFIG.from_dict({}).use()
    assert figure_overrides() == {}


def test_reset_clears_what_the_package_activated(tmp_path):
    CONFIG.load(write(tmp_path)).use()
    CONFIG.reset()
    assert figure_overrides() == {}


def test_reset_of_another_package_keeps_the_overrides(tmp_path):
    other = Schema(package="macro", base={"default": Theme}).config_class()
    CONFIG.load(write(tmp_path)).use()
    other.reset()
    assert "tax_welfare" in figure_overrides()


def test_activate_and_clear_directly():
    econ_toml.activate_figure_overrides(parse(TOML))
    assert "tax_welfare" in figure_overrides()
    econ_toml.activate_figure_overrides(None)
    assert figure_overrides() == {}
    econ_toml.activate_figure_overrides(parse(TOML))
    econ_toml.clear_figure_overrides()
    assert figure_overrides() == {}


def test_module_use_activates_through_entry_points(tmp_path, monkeypatch):
    class EntryPoint:
        @staticmethod
        def load():
            return CONFIG

    monkeypatch.setattr(econ_toml.metadata, "entry_points", lambda group: [EntryPoint()])
    econ_toml.use(write(tmp_path))
    assert figure_overrides("fig.v2") == {"dot.label": Nudge(dy=5)}


# ---- applying to a scene


def scene_of(*layers):
    return Scene(layers)


def test_replaces_the_nudge_of_matching_labels_only():
    point = PointLabelLayer((4, 4), "P", id="dot.label", nudge=Nudge(1, 1))
    text = TextLayer((1, 1), "T", id="t")
    path = PathLayer([(0, 0), (1, 1)], id="line")
    scene = scene_of(point, text, path)
    new = with_label_nudges(
        scene, {"dot.label": Nudge(7, 8), "t": Nudge(2, 3), "line": Nudge(9, 9)}
    )
    assert new.layers[0].nudge == Nudge(7, 8)  # replaced, not added to Nudge(1, 1)
    assert new.layers[1].nudge == Nudge(2, 3)
    assert new.layers[2] is path  # no nudge field: left alone
    assert scene.layers[0].nudge == Nudge(1, 1)  # the original scene is untouched


def test_a_zero_override_cancels_the_layers_own_nudge():
    point = PointLabelLayer((4, 4), "P", id="p", nudge=Nudge(5, 5))
    (new,) = with_label_nudges(scene_of(point), {"p": Nudge()}).layers
    assert new.nudge == Nudge()


def test_unknown_ids_change_nothing():
    scene = scene_of(TextLayer((1, 1), "T", id="t"))
    assert with_label_nudges(scene, {"missing": Nudge(1, 1)}) is scene
    assert with_label_nudges(scene, {}) is scene
    same = scene_of(TextLayer((1, 1), "T", id="t", nudge=Nudge(1, 2)))
    assert with_label_nudges(same, {"t": Nudge(1, 2)}) is same


def test_reaches_labels_inside_groups():
    inner = TextLayer((1, 1), "T", id="inner")
    group = GroupLayer(children=(inner,), id="g")
    (new,) = with_label_nudges(scene_of(group), {"inner": Nudge(1, 1)}).layers
    assert new.children[0].nudge == Nudge(1, 1)
    assert new.id == "g"


def test_a_brace_matches_its_id_and_its_label_id():
    brace = SpanBraceLayer((2, 5), (6, 5), "Gap", id="gap")
    for key in ("gap", "gap.label"):
        (new,) = with_label_nudges(scene_of(brace), {key: Nudge(1, 2)}).layers
        assert new.nudge == Nudge(1, 2)
    # ...unless another layer really has the id "gap.label"
    other = TextLayer((1, 1), "T", id="gap.label")
    new = with_label_nudges(scene_of(brace, other), {"gap.label": Nudge(1, 2)})
    assert new.layers[0].nudge is None
    assert new.layers[1].nudge == Nudge(1, 2)


# ---- applying on save


def svg_text(path: Path) -> str:
    return re.sub(r"<dc:date>.*?</dc:date>", "", path.read_text(encoding="utf-8"), flags=re.S)


def labelled(**nudges: Nudge | None) -> list[Any]:
    return [
        FillLayer([(0, 0), (10, 0), (0, 10)], fill=Fill(opacity=0.2), id="big"),
        FillLayer([(8, 8), (8.3, 8), (8, 8.3)], fill=Fill(opacity=0.2), id="tiny"),
        MarkerLayer([(4, 4)], id="dot"),
        PointLabelLayer((4, 4), "Point", id="dot.label", nudge=nudges.get("dot.label")),
        RegionLabelLayer("big", "Inside", id="big.label", nudge=nudges.get("big.label")),
        RegionLabelLayer(
            "tiny",
            "Callout",
            id="tiny.label",
            placement="callout",
            nudge=nudges.get("tiny.label"),
        ),
        SpanBraceLayer((2, 5), (6, 5), "Gap", id="gap", nudge=nudges.get("gap")),
        TextLayer((5, 9), "Text", offset=(2, 2), id="text", nudge=nudges.get("text")),
    ]


def save(tmp_path: Path, name: str, layers: list[Any]) -> str:
    with matplotlib.rc_context({"svg.hashsalt": "overrides"}):
        Canvas().extend(layers).save(tmp_path / name)
    return svg_text(tmp_path / name)


def activate(figures: dict[str, dict[str, dict[str, Any]]]) -> None:
    CONFIG.from_dict({"figure": figures}).use()


def test_no_active_overrides_leave_the_output_byte_identical(tmp_path):
    plain = save(tmp_path, "tax_welfare.svg", labelled())
    activate({"another": {"label": {"dot.label": {"top": 10}}}})  # a different stem
    assert save(tmp_path, "tax_welfare.svg", labelled()) == plain
    activate({"tax_welfare": {"label": {"nothing.here": {"top": 10}}}})  # unknown id
    assert save(tmp_path, "tax_welfare.svg", labelled()) == plain


def test_save_applies_the_overrides_for_the_files_stem(tmp_path):
    spec = {
        "dot.label": {"top": 10, "left": 4},
        "big.label": {"right": 6},
        "tiny.label": {"top": "3mm"},  # a callout: its leader follows
        "gap": {"bottom": 5},
        "text": {"top": 2},
    }
    nudges = {
        "dot.label": Nudge(-4, 10),
        "big.label": Nudge(6, 0),
        "tiny.label": Nudge(0, 3 * 72 / 25.4),
        "gap": Nudge(0, -5),
        "text": Nudge(0, 2),
    }
    plain = save(tmp_path, "tax_welfare.svg", labelled())
    expected = save(tmp_path, "expected.svg", labelled(**nudges))
    assert expected != plain
    activate({"tax_welfare": {"label": spec}})
    moved = save(tmp_path, "tax_welfare.svg", labelled())
    assert moved == expected  # labels and the callout's leader are exactly as if nudged in code
    assert save(tmp_path, "somewhere_else.svg", labelled()) == plain


def test_the_stem_is_the_output_files_stem_whatever_its_folder_and_format(tmp_path):
    activate({"tax_welfare": {"label": {"text": {"top": 20}}}})
    layers = labelled()
    folder = tmp_path / "principle"
    folder.mkdir()
    expected = save(tmp_path, "expected.svg", labelled(text=Nudge(0, 20)))
    assert save(folder, "tax_welfare.svg", layers) == expected
    plain_png = tmp_path / "other.png"
    moved_png = folder / "tax_welfare.png"
    Canvas().extend(layers).save(plain_png)
    Canvas().extend(layers).save(moved_png)
    assert plain_png.read_bytes() != moved_png.read_bytes()


def test_overrides_replace_the_layers_own_nudge(tmp_path):
    activate({"fig": {"label": {"text": {"top": 20}}}})
    own = labelled(text=Nudge(30, 0))
    got = save(tmp_path, "fig.svg", own)
    assert got == save(tmp_path, "expected.svg", labelled(text=Nudge(0, 20)))


def test_save_does_not_change_the_canvas(tmp_path):
    activate({"fig": {"label": {"text": {"top": 20}}}})
    canvas = Canvas().extend(labelled())
    before = canvas.snapshot()
    canvas.save(tmp_path / "fig.svg")
    assert canvas.snapshot() is before
    assert canvas.snapshot().layers[-1].nudge is None


def test_render_without_a_path_does_not_apply_overrides():
    activate({"fig": {"label": {"text": {"top": 20}}}})
    seen = Canvas().extend(labelled()).render()
    try:
        (text,) = [t for t in seen.axes.texts if t.get_gid() == "text"]
        reference = Canvas().extend(labelled()).render()
        try:
            (other,) = [t for t in reference.axes.texts if t.get_gid() == "text"]
            assert text.get_position() == other.get_position()
        finally:
            reference.close()
    finally:
        seen.close()


class Recorder:
    name = "recorder"

    def __init__(self) -> None:
        self.scenes: list[Scene] = []

    def render(self, scene, context):
        self.scenes.append(scene)
        return scene

    def save(self, result, target, options):
        return [target]


def test_other_renderers_get_the_overridden_scene(tmp_path):
    activate({"fig": {"label": {"text": {"top": 20}}}})
    recorder = Recorder()
    Canvas(renderer=recorder).add(TextLayer((1, 1), "T", id="text")).save(tmp_path / "fig.svg")
    assert recorder.scenes[0].layers[0].nudge == Nudge(0, 20)


def test_tex_export_applies_text_overrides(tmp_path):
    canvas = Canvas().add(TextLayer((1, 1), "T", id="text"))
    canvas.save(tmp_path / "plain.tex")
    activate({"fig": {"label": {"text": {"top": 20}}}})
    canvas.save(tmp_path / "fig.tex")
    assert "yshift=20pt" in (tmp_path / "fig.tex").read_text()
    assert "yshift=20pt" not in (tmp_path / "plain.tex").read_text()


def test_grid_save_applies_to_the_labels_of_every_cell(tmp_path):
    def cell(**nudges):
        return Canvas().extend(labelled(**nudges))

    def grid_svg(name, cells):
        with matplotlib.rc_context({"svg.hashsalt": "overrides"}):
            CanvasGrid(cells, cols=2).save(tmp_path / name)
        return svg_text(tmp_path / name)

    plain = grid_svg("grid.svg", [cell(), cell()])
    expected = grid_svg("expected.svg", [cell(text=Nudge(0, 20)), cell(text=Nudge(0, 20))])
    assert expected != plain
    activate({"grid": {"label": {"text": {"top": 20}}}})
    grid = CanvasGrid([cell(), cell()], cols=2)
    with matplotlib.rc_context({"svg.hashsalt": "overrides"}):
        grid.save(tmp_path / "grid.svg")
    assert svg_text(tmp_path / "grid.svg") == expected
    assert grid.placements[0].canvas.snapshot().layers[-1].nudge is None
    with matplotlib.rc_context({"svg.hashsalt": "overrides"}):
        grid.save(tmp_path / "other.svg")
    assert svg_text(tmp_path / "other.svg") == plain


def test_grid_with_no_matching_overrides_is_unchanged(tmp_path):
    grid = CanvasGrid([Canvas().extend(labelled())])
    assert grid._for_file(tmp_path / "grid.svg") is grid
    activate({"grid": {"label": {"nope": {"top": 20}}}})
    assert grid._for_file(tmp_path / "grid.svg") is grid


# ---- label ids in the drawn SVG


def element_ids(path: Path) -> list[str]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    return [e.get("id") for e in root.iter() if e.get("id")]  # type: ignore[misc]


def test_every_label_carries_its_layer_id_in_the_svg(tmp_path):
    layers = [
        *labelled(),
        PointLabelLayer((3, 2), "$x^2$", id="math.label"),
        TextLayer((5, 8), "$y$", id="mtext"),
    ]
    path = tmp_path / "ids.svg"
    Canvas().extend(layers).save(path)
    ids = element_ids(path)
    assert len(ids) == len(set(ids))  # unique
    for label in ("dot.label", "big.label", "tiny.label", "math.label", "text", "mtext"):
        assert label in ids
    assert "tiny.label.leader" in ids
    assert {"gap", "gap.label"} <= set(ids)  # a brace: the outline is `id`, its label `id.label`


def test_a_label_id_marks_the_group_that_draws_the_text(tmp_path):
    path = tmp_path / "ids.svg"
    Canvas().extend(labelled()).save(path)
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    for element in root.iter():
        if element.get("id") == "dot.label":
            assert element.tag.endswith("}g")
            assert len(list(element.iter())) > 1  # the glyphs are inside it
            break
    else:
        pytest.fail("dot.label not found")


# ---- braces drawn in the axis gutter


def braced(**nudges: Nudge | None) -> list[Any]:
    return [
        BraceLayer("y", 2, 6, "Wedge", side="outside", id="wedge", nudge=nudges.get("wedge")),
        BraceLayer("x", 2, 6, "Policy", side="outside", id="policy", nudge=nudges.get("policy")),
        BraceLayer("y", 7, 9, "Inner", side="inside", id="inner", nudge=nudges.get("inner")),
    ]


def test_override_moves_a_gutter_brace_label_as_if_nudged_in_code(tmp_path):
    outer_plain = save(tmp_path, "o.svg", braced()[:2])
    assert save(tmp_path, "o.svg", braced(wedge=Nudge(0, 8))[:2]) != outer_plain
    assert save(tmp_path, "o.svg", braced(policy=Nudge(0, 8))[:2]) != outer_plain
    plain = save(tmp_path, "brace_fig.svg", braced())
    expected = save(
        tmp_path, "expected.svg", braced(wedge=Nudge(-3, 8), policy=Nudge(0, -4), inner=Nudge(5, 0))
    )
    assert expected != plain
    spec = {
        "wedge": {"top": 8, "left": 3},
        "policy.label": {"bottom": 4},  # the id the label has in the SVG
        "inner": {"right": 5},
    }
    activate({"brace_fig": {"label": spec}})
    assert save(tmp_path, "brace_fig.svg", braced()) == expected
    assert save(tmp_path, "other.svg", braced()) == plain


def test_gutter_brace_override_leaves_the_outline_in_place(tmp_path):
    def outline(text: str, gid: str) -> str:
        root = ET.fromstring(text)
        return next(ET.tostring(e) for e in root.iter() if e.get("id") == gid).decode()

    plain = save(tmp_path, "brace_fig.svg", braced())
    moved = save(tmp_path, "moved.svg", braced(wedge=Nudge(0, 12)))
    assert outline(moved, "wedge") == outline(plain, "wedge")
    assert outline(moved, "wedge.label") != outline(plain, "wedge.label")
