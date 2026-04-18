"""Tests for db_cli.cli commands."""

import shutil
from pathlib import Path

import pytest

from db_cli.cli import get_version, validate_file, xml_to_dsb

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
SAMPLE_XML = SAMPLES_DIR / "EmptySite.xml"


@pytest.fixture
def tmp_xml(tmp_path):
    """Copy sample XML to a temp directory and return the path."""
    dest = tmp_path / SAMPLE_XML.name
    shutil.copy(SAMPLE_XML, dest)
    return dest


def test_version(tmp_xml):
    result = get_version(str(tmp_xml))
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_validate(tmp_xml):
    result = validate_file(str(tmp_xml))
    assert "Validation successful" in result


def test_xml_to_dsb_raises():
    with pytest.raises(NotImplementedError):
        xml_to_dsb("any_file.xml")
