"""Tests for db_cli.cli commands."""

import json
import shutil
from pathlib import Path

import pytest

from db_cli.cli import get_version, validate_file, xml_to_json, json_to_xml, xml_to_dsb

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


def test_xml_to_json(tmp_xml):
    xml_to_json(str(tmp_xml))
    json_path = tmp_xml.with_suffix(".json")
    assert json_path.is_file()
    with open(json_path) as f:
        data = json.load(f)
    assert "dsbJSON" in data


def test_json_to_xml(tmp_xml):
    # First convert to JSON
    xml_to_json(str(tmp_xml))
    json_path = tmp_xml.with_suffix(".json")

    # Remove original XML
    tmp_xml.unlink()

    # Convert back to XML
    json_to_xml(str(json_path))
    assert tmp_xml.is_file()


def test_xml_to_json_roundtrip(tmp_xml):
    """Verify version is preserved after xml -> json -> xml roundtrip."""
    original_version = get_version(str(tmp_xml))

    xml_to_json(str(tmp_xml))
    json_path = tmp_xml.with_suffix(".json")
    json_version = get_version(str(json_path))

    tmp_xml.unlink()
    json_to_xml(str(json_path))
    roundtrip_version = get_version(str(tmp_xml))

    assert original_version == json_version
    assert original_version == roundtrip_version


def test_xml_to_dsb_raises():
    with pytest.raises(NotImplementedError):
        xml_to_dsb("any_file.xml")
