import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import mosaickit


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
            "import sys; import mosaickit; "
            "assert 'matplotlib' not in sys.modules; "
            "assert 'econ_viz' not in sys.modules",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
