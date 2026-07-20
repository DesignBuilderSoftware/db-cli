"""Unit tests for db_cli.converter core logic.

DesignBuilder.exe is never launched: ``run_async``, ``kill_process`` and
``kill_when_idle`` are monkeypatched in the converter module's namespace so
the orchestration logic (path validation, output detection, cleanup,
move-to-destination) is tested in isolation.
"""

import time

import pytest

import db_cli.converter as converter
from db_cli.converter import _find_new_dsb, _wait_for_file


@pytest.fixture
def no_sleep(monkeypatch):
    """Disable the post-kill filesystem-flush delay in xml_to_dsb."""
    monkeypatch.setattr(converter.time, "sleep", lambda s: None)


class FakeProcess:
    """Stands in for the handle returned by db_process.run_async."""


# ---------------------------------------------------------------------------
# _wait_for_file
# ---------------------------------------------------------------------------


class TestWaitForFile:
    def test_existing_non_empty_file_returns_true_immediately(self, tmp_path):
        f = tmp_path / "out.xml"
        f.write_text("<dsbXML/>")
        start = time.monotonic()
        assert _wait_for_file(f, timeout=5, poll_interval=0.01) is True
        assert time.monotonic() - start < 1

    def test_missing_file_times_out(self, tmp_path):
        f = tmp_path / "never.xml"
        assert _wait_for_file(f, timeout=0.05, poll_interval=0.01) is False

    def test_empty_file_is_not_accepted(self, tmp_path):
        f = tmp_path / "empty.xml"
        f.touch()
        assert _wait_for_file(f, timeout=0.05, poll_interval=0.01) is False

    def test_file_appearing_during_poll_returns_true(self, tmp_path, monkeypatch):
        f = tmp_path / "late.xml"
        polls = {"n": 0}
        real_sleep = time.sleep

        def sleeping_creator(interval):
            polls["n"] += 1
            if polls["n"] == 2:
                f.write_text("<dsbXML/>")
            real_sleep(0)

        monkeypatch.setattr(converter.time, "sleep", sleeping_creator)
        assert _wait_for_file(f, timeout=5, poll_interval=0.01) is True


# ---------------------------------------------------------------------------
# _find_new_dsb
# ---------------------------------------------------------------------------


class TestFindNewDsb:
    def test_prefers_exact_stem(self, tmp_path):
        exact = tmp_path / "Model.dsb"
        exact.write_text("x")
        suffixed = tmp_path / "Model 1.dsb"
        suffixed.write_text("x")
        assert _find_new_dsb(tmp_path, set(), "Model") == exact

    def test_falls_back_to_space_1_variant(self, tmp_path):
        suffixed = tmp_path / "Model 1.dsb"
        suffixed.write_text("x")
        assert _find_new_dsb(tmp_path, set(), "Model") == suffixed

    def test_falls_back_to_any_new_dsb(self, tmp_path):
        other = tmp_path / "SomethingElse.dsb"
        other.write_text("x")
        assert _find_new_dsb(tmp_path, set(), "Model") == other

    def test_ignores_pre_existing_files(self, tmp_path):
        old = tmp_path / "Model.dsb"
        old.write_text("x")
        assert _find_new_dsb(tmp_path, {old}, "Model") is None

    def test_returns_none_when_directory_empty(self, tmp_path):
        assert _find_new_dsb(tmp_path, set(), "Model") is None


# ---------------------------------------------------------------------------
# dsb_to_xml
# ---------------------------------------------------------------------------


class TestDsbToXml:
    @pytest.fixture
    def dsb_file(self, tmp_path):
        f = tmp_path / "Model.dsb"
        f.write_bytes(b"fake dsb zip content")
        return f

    def _patch_run(self, monkeypatch, side_effect=None):
        """Patch run_async/kill_process, recording calls."""
        calls = {"run_async": [], "kill_process": 0}

        def fake_run_async(path, *commands, exe_path=None):
            calls["run_async"].append({"path": path, "exe_path": exe_path})
            if side_effect is not None:
                side_effect(path)
            return FakeProcess()

        def fake_kill_process():
            calls["kill_process"] += 1
            return True

        monkeypatch.setattr(converter, "run_async", fake_run_async)
        monkeypatch.setattr(converter, "kill_process", fake_kill_process)
        return calls

    def test_missing_input_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="DSB file not found"):
            converter.dsb_to_xml(str(tmp_path / "missing.dsb"))

    def test_wrong_extension_raises_value_error(self, tmp_path):
        f = tmp_path / "model.txt"
        f.write_text("x")
        with pytest.raises(ValueError, match=r"Expected a \.dsb file"):
            converter.dsb_to_xml(str(f))

    def test_success_returns_xml_next_to_dsb(self, monkeypatch, dsb_file):
        expected_xml = dsb_file.with_suffix(".xml")

        def create_output(path):
            expected_xml.write_text("<dsbXML/>")

        calls = self._patch_run(monkeypatch, side_effect=create_output)
        result = converter.dsb_to_xml(str(dsb_file), timeout=5)
        assert result == expected_xml
        assert result.is_file()
        # DesignBuilder must always be killed afterwards
        assert calls["kill_process"] == 1
        assert calls["run_async"][0]["path"] == dsb_file.resolve()

    def test_exe_path_is_forwarded(self, monkeypatch, dsb_file):
        def create_output(path):
            dsb_file.with_suffix(".xml").write_text("<dsbXML/>")

        calls = self._patch_run(monkeypatch, side_effect=create_output)
        converter.dsb_to_xml(str(dsb_file), exe_path="C:/DB/DesignBuilder.exe", timeout=5)
        assert calls["run_async"][0]["exe_path"] == "C:/DB/DesignBuilder.exe"

    def test_output_filepath_moves_result(self, monkeypatch, dsb_file, tmp_path):
        def create_output(path):
            dsb_file.with_suffix(".xml").write_text("<dsbXML/>")

        self._patch_run(monkeypatch, side_effect=create_output)
        dest = tmp_path / "nested" / "dir" / "final.xml"
        result = converter.dsb_to_xml(str(dsb_file), output_filepath=str(dest), timeout=5)
        assert result == dest.resolve()
        assert dest.is_file()
        # original was moved, not copied
        assert not dsb_file.with_suffix(".xml").exists()

    def test_timeout_raises_and_still_kills_process(self, monkeypatch, dsb_file):
        # run_async never produces the output file
        calls = self._patch_run(monkeypatch)
        with pytest.raises(FileNotFoundError, match="did not produce the expected output"):
            converter.dsb_to_xml(str(dsb_file), timeout=0.05)
        assert calls["kill_process"] == 1


# ---------------------------------------------------------------------------
# xml_to_dsb (converter-level; the CLI wrapper intentionally blocks this)
# ---------------------------------------------------------------------------


class TestXmlToDsbConverter:
    @pytest.fixture
    def xml_file(self, tmp_path):
        f = tmp_path / "Model.xml"
        f.write_text("<dsbXML/>")
        return f

    def _patch_run(self, monkeypatch, side_effect=None, idle_raises=False):
        calls = {"run_async": [], "kill_process": 0, "kill_when_idle": 0}

        def fake_run_async(path, *commands, exe_path=None):
            calls["run_async"].append({"path": path, "exe_path": exe_path})
            if side_effect is not None:
                side_effect(path)
            return FakeProcess()

        def fake_kill_when_idle(startup_period=None):
            calls["kill_when_idle"] += 1
            if idle_raises:
                raise RuntimeError("idle detection failed")

        def fake_kill_process():
            calls["kill_process"] += 1
            return True

        monkeypatch.setattr(converter, "run_async", fake_run_async)
        monkeypatch.setattr(converter, "kill_when_idle", fake_kill_when_idle)
        monkeypatch.setattr(converter, "kill_process", fake_kill_process)
        return calls

    def test_missing_input_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="XML file not found"):
            converter.xml_to_dsb(str(tmp_path / "missing.xml"))

    def test_wrong_extension_raises_value_error(self, tmp_path):
        f = tmp_path / "model.dsb"
        f.write_text("x")
        with pytest.raises(ValueError, match=r"Expected a \.xml file"):
            converter.xml_to_dsb(str(f))

    def test_success_finds_suffixed_dsb(self, monkeypatch, xml_file, no_sleep):
        created = xml_file.parent / "Model 1.dsb"

        def create_output(path):
            created.write_bytes(b"dsb")

        calls = self._patch_run(monkeypatch, side_effect=create_output)
        result = converter.xml_to_dsb(str(xml_file), timeout=1)
        assert result == created
        assert calls["kill_when_idle"] == 1
        assert calls["run_async"][0]["path"] == xml_file.resolve()

    def test_idle_detection_failure_falls_back_to_kill(
        self, monkeypatch, xml_file, no_sleep
    ):
        created = xml_file.parent / "Model.dsb"

        def create_output(path):
            created.write_bytes(b"dsb")

        calls = self._patch_run(monkeypatch, side_effect=create_output, idle_raises=True)
        result = converter.xml_to_dsb(str(xml_file), timeout=1)
        assert result == created
        assert calls["kill_process"] == 1

    def test_pre_existing_dsb_is_not_mistaken_for_output(
        self, monkeypatch, xml_file, no_sleep
    ):
        old = xml_file.parent / "Old.dsb"
        old.write_bytes(b"old")
        self._patch_run(monkeypatch)
        with pytest.raises(FileNotFoundError, match=r"did not produce a \.dsb file"):
            converter.xml_to_dsb(str(xml_file), timeout=1)

    def test_output_filepath_moves_result(self, monkeypatch, xml_file, tmp_path, no_sleep):
        created = xml_file.parent / "Model 1.dsb"

        def create_output(path):
            created.write_bytes(b"dsb")

        self._patch_run(monkeypatch, side_effect=create_output)
        dest = tmp_path / "out" / "Final.dsb"
        result = converter.xml_to_dsb(str(xml_file), output_filepath=str(dest), timeout=1)
        assert result == dest.resolve()
        assert dest.is_file()
        assert not created.exists()

    def test_no_output_raises_file_not_found(self, monkeypatch, xml_file, no_sleep):
        self._patch_run(monkeypatch)
        with pytest.raises(FileNotFoundError, match=r"did not produce a \.dsb file"):
            converter.xml_to_dsb(str(xml_file), timeout=1)
