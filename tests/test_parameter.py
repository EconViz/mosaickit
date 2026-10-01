import pytest

from mosaickit import BindingError, Canvas, Constant, Parameter, PathLayer, TextLayer


def test_expression_structure_arithmetic_and_comparison():
    x, y = Parameter("x"), Parameter("y")
    first = (x + y) * 2 - 1
    second = (Parameter("x") + Parameter("y")) * 2 - 1
    assert first == second
    assert hash(first) == hash(second)
    assert first.evaluate({x: 3, y: 4}) == 13
    assert (2 / x + 3 * x - x**2).evaluate({x: 2}) == 3
    assert (x < y).evaluate({x: 1, y: 2})
    assert x.equals(2).evaluate({x: 2})
    with pytest.raises(BindingError):
        bool(x < y)


def test_binding_errors_name_parameter():
    x = Parameter("price", value_type=float)
    with pytest.raises(BindingError, match="price"):
        x.evaluate({})
    with pytest.raises(BindingError, match="price"):
        x.evaluate({x: "wrong"})
    with pytest.raises(BindingError, match="price"):
        (x + 1).evaluate({x: "wrong"})
    with pytest.raises(BindingError):
        Constant([])


def test_partial_scene_binding_preserves_source_and_ids():
    x, y = Parameter("x"), Parameter("y")
    canvas = Canvas().add(TextLayer((x + y, 2), "point", id="text"))
    partial = canvas.bind(x, 3)
    assert partial.snapshot().layers[0].position[0].free_parameters() == frozenset({y})
    bound = partial.bind(y, 4)
    assert bound.snapshot().layers[0].position == (7.0, 2.0)
    assert bound.snapshot().layers[0].id == "text"
    assert canvas.snapshot().layers[0].position[0].free_parameters() == frozenset({x, y})


def test_binding_path_coordinates_and_parameter_values():
    x = Parameter("x")
    canvas = Canvas().add(PathLayer([(0, 0), (x, 2)]))
    assert canvas.bind(x, 3).snapshot().layers[0].path[-1] == (3.0, 2.0)
    assert x.values([1, 2]).values == (1, 2)


def test_render_reports_unbound_parameters():
    price = Parameter("price")
    canvas = Canvas().add(PathLayer([(0, 0), (price, 2)]))
    with pytest.raises(BindingError, match="price"):
        canvas.render()
