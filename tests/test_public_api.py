import subprocess
import sys
from importlib.metadata import requires, version
from pathlib import Path

import pytest

import mosaickit
from mosaickit import Canvas, RendererRegistry, RenderError


def test_public_exports_and_typing_marker():
    assert mosaickit.__version__ == version("mosaickit")
    assert Path(mosaickit.__file__).with_name("py.typed").is_file()
    assert all(hasattr(mosaickit, name) for name in mosaickit.__all__)
    for name in ("_RenderContext", "_RenderPlan", "_ResolvedLayer", "AxesLayer"):
        assert not hasattr(mosaickit, name)


def test_root_import_does_not_load_matplotlib_or_domain_packages():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, warnings; warnings.simplefilter('error', DeprecationWarning); "
            "import mosaickit; "
            "assert 'matplotlib' not in sys.modules; "
            "assert 'kinetickit' not in sys.modules; "
            "assert 'econ_viz' not in sys.modules",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_distribution_has_no_bezierkit_dependency():
    dependencies = requires("mosaickit") or []
    assert not any(requirement.lower().startswith("bezierkit") for requirement in dependencies)


def test_distribution_requires_glyphkit_without_kinetickit():
    dependencies = requires("mosaickit") or []
    glyphkit = [item for item in dependencies if item.lower().startswith("glyphkit")]
    # Build backends may normalize the ordering of version specifiers.
    assert len(glyphkit) == 1
    assert glyphkit[0] in ("glyphkit>=1.0.0b3,<2", "glyphkit<2,>=1.0.0b3")
    assert not any(item.lower().startswith("kinetickit") for item in dependencies)


def test_tikz_is_an_export_format_but_not_a_builtin_renderer(tmp_path):
    with pytest.raises(RenderError, match="Unknown renderer"):
        RendererRegistry().get("tikz")
    assert Canvas().save(tmp_path / "figure.tex") == [tmp_path / "figure.tex"]
    with pytest.raises(RenderError, match="Unsupported output format"):
        Canvas().save(tmp_path / "figure.pgf")
