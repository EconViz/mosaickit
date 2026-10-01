import subprocess
from email import policy
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture(scope="module")
def wheel_metadata(tmp_path_factory):
    project_root = Path(__file__).parents[1]
    output_dir = tmp_path_factory.mktemp("wheel")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(output_dir)],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel_path = next(output_dir.glob("*.whl"))

    with ZipFile(wheel_path) as wheel:
        metadata_path = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        return BytesParser(policy=policy.default).parsebytes(wheel.read(metadata_path))


def test_wheel_description_uses_absolute_banner_url(wheel_metadata):
    description = wheel_metadata.get_payload()

    assert (
        '<img src="https://raw.githubusercontent.com/EconViz/mosaickit/main/assets/banner.svg"'
        in description
    )


def test_wheel_metadata_includes_repository_url(wheel_metadata):
    project_urls = wheel_metadata.get_all("Project-URL", [])

    assert "Repository, https://github.com/EconViz/mosaickit" in project_urls
