"""Tests for db_cli.cli commands."""

import shutil
from pathlib import Path

import pytest

from db_cli.cli import get_version, validate_file, xml_to_dsb

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
SAMPLE_XML = SAMPLES_DIR / "EmptySite.xml"

# The sample-dependent tests are skipped: EmptySite.xml is missing and the
# checked-in Shoebox*.xml samples are malformed (lxml fails to parse them).
# Restore these once a valid dsbXML fixture is added.
_needs_valid_sample = pytest.mark.skipif(
    not SAMPLE_XML.exists(),
    reason="No valid dsbXML sample available (see corrupt-samples issue)",
)


@pytest.fixture
def tmp_xml(tmp_path):
    """Copy sample XML to a temp directory and return the path."""
    dest = tmp_path / SAMPLE_XML.name
    shutil.copy(SAMPLE_XML, dest)
    return dest


@_needs_valid_sample
def test_version(tmp_xml):
    result = get_version(str(tmp_xml))
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@_needs_valid_sample
def test_validate(tmp_xml):
    result = validate_file(str(tmp_xml))
    assert "Validation successful" in result


def test_xml_to_dsb_raises():
    with pytest.raises(NotImplementedError):
        xml_to_dsb("any_file.xml")
