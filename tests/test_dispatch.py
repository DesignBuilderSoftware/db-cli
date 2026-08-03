"""Tests for command-line argument parsing and command dispatch.

db_cli uses python-fire; ``main()`` builds a command dict and hands it to
``Fire``.  These tests drive ``main()`` in-process by patching ``sys.argv``
(no subprocesses) and capture what Fire prints.
"""

import sys

import pytest

import db_cli.cli as cli


def run_cli(monkeypatch, capsys, *argv):
    """Invoke cli.main() with the given argv and return captured output."""
    monkeypatch.setattr(sys, "argv", ["db-cli", *argv])
    cli.main()
    return capsys.readouterr()


# ---------------------------------------------------------------------------
# Dispatch to each command
# ---------------------------------------------------------------------------


def test_version_command_positional_arg(monkeypatch, capsys, valid_xml):
    out = run_cli(monkeypatch, capsys, "version", str(valid_xml)).out
    assert "2026.1.0.010" in out


def test_version_command_named_flag(monkeypatch, capsys, valid_xml):
    out = run_cli(monkeypatch, capsys, "version", "--filepath", str(valid_xml)).out
    assert "2026.1.0.010" in out


def test_validate_command_dispatches_to_validate_file(monkeypatch, capsys):
    class FakeModel:
        version = "5.5.5"

    monkeypatch.setattr(cli, "load_model", lambda fp: FakeModel())
    out = run_cli(monkeypatch, capsys, "validate", "model.xml").out
    assert "Validation successful, file saved in version 5.5.5." in out


def test_close_command_dispatches_to_kill_process(monkeypatch, capsys):
    monkeypatch.setattr(cli, "kill_process", lambda: True)
    out = run_cli(monkeypatch, capsys, "close").out
    assert "DesignBuilder process closed." in out


def test_dsb2xml_command_forwards_flags(monkeypatch, capsys):
    recorded = {}

    def fake_converter(dsb_filepath, output_filepath=None, exe_path=None):
        recorded["dsb_filepath"] = dsb_filepath
        recorded["output_filepath"] = output_filepath
        recorded["exe_path"] = exe_path
        return "result.xml"

    monkeypatch.setattr(cli, "_dsb_to_xml", fake_converter)
    out = run_cli(
        monkeypatch,
        capsys,
        "dsb2xml",
        "model.dsb",
        "--output",
        "out.xml",
        "--exe",
        "DB.exe",
    ).out
    assert "Exported: result.xml" in out
    assert recorded == {
        "dsb_filepath": "model.dsb",
        "output_filepath": "out.xml",
        "exe_path": "DB.exe",
    }


def test_xml2dsb_command_raises_not_implemented(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["db-cli", "xml2dsb", "model.xml"])
    with pytest.raises(NotImplementedError, match="xml2dsb is not working"):
        cli.main()


# ---------------------------------------------------------------------------
# Parse errors
# ---------------------------------------------------------------------------


def test_unknown_command_exits_with_code_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["db-cli", "does-not-exist"])
    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert excinfo.value.code == 2


def test_missing_required_argument_exits_with_code_2(monkeypatch, capsys):
    # `version` requires a filepath
    monkeypatch.setattr(sys, "argv", ["db-cli", "version"])
    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert excinfo.value.code == 2


def test_unexpected_extra_argument_exits_with_code_2(monkeypatch, capsys, valid_xml):
    monkeypatch.setattr(sys, "argv", ["db-cli", "version", str(valid_xml), "surplus-arg"])
    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert excinfo.value.code == 2


def test_all_expected_commands_are_registered(monkeypatch):
    """main() should expose exactly the documented command names."""
    registered = {}

    def fake_fire(component=None, *args, **kwargs):
        registered.update(component)

    monkeypatch.setattr(cli, "Fire", fake_fire)
    cli.main()
    assert set(registered) == {"version", "validate", "dsb2xml", "xml2dsb", "close"}
    assert registered["version"] is cli.get_version
    assert registered["validate"] is cli.validate_file
    assert registered["dsb2xml"] is cli.dsb_to_xml
    assert registered["xml2dsb"] is cli.xml_to_dsb
    assert registered["close"] is cli.close
