"""Unit tests for the individual command functions in db_cli.cli.

These call the library API directly (no subprocesses) and monkeypatch the
external collaborators (schema utils, converter, db_process) so only the
CLI module's own logic is under test.
"""

import pytest

import db_cli.cli as cli

SAMPLE_VERSION = "2026.1.0.010"  # matches conftest.VALID_DSBXML


# ---------------------------------------------------------------------------
# get_version
# ---------------------------------------------------------------------------


class TestGetVersion:
    def test_returns_version_from_valid_file(self, valid_xml):
        assert cli.get_version(str(valid_xml)) == SAMPLE_VERSION

    def test_malformed_xml_raises_runtime_error(self, malformed_xml):
        with pytest.raises(RuntimeError) as excinfo:
            cli.get_version(str(malformed_xml))
        assert "Failed to parse XML file" in str(excinfo.value)
        assert str(malformed_xml) in str(excinfo.value)

    def test_missing_file_raises_runtime_error(self, tmp_path):
        missing = tmp_path / "nope.xml"
        with pytest.raises(RuntimeError, match="Failed to parse XML file"):
            cli.get_version(str(missing))

    def test_missing_dsbxml_key_raises_runtime_error(self, wrong_root_xml):
        with pytest.raises(RuntimeError) as excinfo:
            cli.get_version(str(wrong_root_xml))
        assert "Can't find dsbXML" in str(excinfo.value)
        # The message should list the keys that were actually found
        assert "NotDsbXML" in str(excinfo.value)

    def test_uses_file_to_dict_result(self, monkeypatch):
        """Pure unit test: version is read from dictionary['dsbXML']['version']."""
        monkeypatch.setattr(cli, "file_to_dict", lambda fp: {"dsbXML": {"version": "9.9.9"}})
        assert cli.get_version("whatever.xml") == "9.9.9"


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------


class TestValidateFile:
    def test_success_message_includes_model_version(self, monkeypatch):
        class FakeModel:
            version = "7.1.2"

        calls = []

        def fake_load_model(filepath):
            calls.append(filepath)
            return FakeModel()

        monkeypatch.setattr(cli, "load_model", fake_load_model)
        result = cli.validate_file("model.xml")
        assert result == "Validation successful, file saved in version 7.1.2."
        assert calls == ["model.xml"]

    def test_validation_error_propagates(self, monkeypatch):
        def fake_load_model(filepath):
            raise ValueError("schema violation")

        monkeypatch.setattr(cli, "load_model", fake_load_model)
        with pytest.raises(ValueError, match="schema violation"):
            cli.validate_file("model.xml")


# ---------------------------------------------------------------------------
# dsb_to_xml (thin CLI wrapper around converter.dsb_to_xml)
# ---------------------------------------------------------------------------


class TestDsbToXmlWrapper:
    def test_returns_exported_message_and_forwards_args(self, monkeypatch):
        recorded = {}

        def fake_converter(dsb_filepath, output_filepath=None, exe_path=None):
            recorded["dsb_filepath"] = dsb_filepath
            recorded["output_filepath"] = output_filepath
            recorded["exe_path"] = exe_path
            return "C:/out/Model.xml"

        monkeypatch.setattr(cli, "_dsb_to_xml", fake_converter)
        result = cli.dsb_to_xml("in.dsb", output="out.xml", exe="DB.exe")
        assert result == "Exported: C:/out/Model.xml"
        assert recorded == {
            "dsb_filepath": "in.dsb",
            "output_filepath": "out.xml",
            "exe_path": "DB.exe",
        }

    def test_defaults_are_none(self, monkeypatch):
        recorded = {}

        def fake_converter(dsb_filepath, output_filepath=None, exe_path=None):
            recorded["output_filepath"] = output_filepath
            recorded["exe_path"] = exe_path
            return "x.xml"

        monkeypatch.setattr(cli, "_dsb_to_xml", fake_converter)
        cli.dsb_to_xml("in.dsb")
        assert recorded == {"output_filepath": None, "exe_path": None}

    def test_converter_error_propagates(self, monkeypatch):
        def fake_converter(*args, **kwargs):
            raise FileNotFoundError("DSB file not found")

        monkeypatch.setattr(cli, "_dsb_to_xml", fake_converter)
        with pytest.raises(FileNotFoundError, match="DSB file not found"):
            cli.dsb_to_xml("missing.dsb")


# ---------------------------------------------------------------------------
# xml_to_dsb
# ---------------------------------------------------------------------------


class TestXmlToDsb:
    def test_always_raises_not_implemented(self):
        with pytest.raises(NotImplementedError) as excinfo:
            cli.xml_to_dsb("any.xml")
        assert "xml2dsb is not working" in str(excinfo.value)

    def test_raises_even_with_all_arguments(self):
        with pytest.raises(NotImplementedError):
            cli.xml_to_dsb("any.xml", output="out.dsb", exe="DB.exe")


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_process_found_and_killed(self, monkeypatch):
        monkeypatch.setattr(cli, "kill_process", lambda: True)
        assert cli.close() == "DesignBuilder process closed."

    def test_no_process_found(self, monkeypatch):
        monkeypatch.setattr(cli, "kill_process", lambda: False)
        assert cli.close() == "No DesignBuilder process found."
