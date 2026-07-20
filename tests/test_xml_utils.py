"""Tests for the db_cli.xml_utils helpers."""

import pytest

from db_cli.xml_utils import dict_to_file, file_to_dict


def test_file_to_dict_returns_root_tag_and_attributes(valid_xml):
    result = file_to_dict(str(valid_xml))
    assert list(result.keys()) == ["dsbXML"]
    assert result["dsbXML"]["version"] == "2026.1.0.010"
    assert result["dsbXML"]["name"] == "~Shoebox"


def test_file_to_dict_raises_on_malformed_xml(malformed_xml):
    with pytest.raises(Exception):
        file_to_dict(str(malformed_xml))


def test_round_trip(tmp_path):
    data = {"dsbXML": {"version": "9.9.9", "objects": "all"}}
    path = tmp_path / "out.xml"
    dict_to_file(data, str(path))
    assert file_to_dict(str(path)) == data


def test_dict_to_file_rejects_multiple_roots(tmp_path):
    with pytest.raises(ValueError, match="single root"):
        dict_to_file({"a": {}, "b": {}}, str(tmp_path / "bad.xml"))
