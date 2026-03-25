"""
converter.py
====================================
Functions to call the DesignBuilder application CLI for operations
that require the proprietary binary format (.dsb / .skh).

DSB files are ZIP archives containing binary .skh files that cannot
be parsed directly. These functions invoke DesignBuilder.exe as a
subprocess to perform the conversions.

CLI reference (from DB-5213):
    DesignBuilder <file.dsb> /process=miFExportAsXML   -> exports .xml
    DesignBuilder <file.xml>                            -> imports to .dsb
    DesignBuilder <file.xml> /process=miFExportAsXML   -> round-trip xml->dsb->xml

Note: DesignBuilder is a GUI application that does NOT exit after
processing.

For **dsb -> xml** (export with ``/process=miFExportAsXML``), the XML
file is written to disk while DB is still running, so we poll for it
and kill the process once it appears.

For **xml -> dsb** (import by opening the XML), DB only writes the
``.dsb`` once its import work is complete.  We use ``kill_when_idle``
to wait for CPU activity to drop, then kill the process and look for
the output file.
"""

import shutil
import time
from pathlib import Path
from typing import Optional

from db_process import export_xml, kill_process, kill_when_idle, run_async


def _wait_for_file(
    path: Path,
    timeout: float = 120,
    poll_interval: float = 1.0,
) -> bool:
    """Block until *path* exists and is non-empty, or *timeout* expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size > 0:
            return True
        time.sleep(poll_interval)
    return False


def _find_new_dsb(
    directory: Path,
    existing: set[Path],
    stem: str,
) -> Optional[Path]:
    """Find a newly created .dsb file in *directory*.

    Checks for the exact-stem and " 1" suffixed variants first,
    then falls back to any new .dsb file.
    """
    candidates = [
        directory / f"{stem}.dsb",
        directory / f"{stem} 1.dsb",
    ]
    # Check known candidates first
    for c in candidates:
        if c.is_file() and c not in existing:
            return c
    # Fallback: any new .dsb
    new_dsbs = set(directory.glob("*.dsb")) - existing
    if new_dsbs:
        return next(iter(new_dsbs))
    return None


def dsb_to_xml(
    dsb_filepath: str,
    output_filepath: Optional[str] = None,
    exe_path: Optional[str] = None,
    timeout: float = 120,
) -> Path:
    """Convert a .dsb file to .xml (dbXML) using DesignBuilder CLI.

    Calls: DesignBuilder <file.dsb> /process=miFExportAsXML

    DesignBuilder exports the XML with the same stem name as the .dsb
    in the same directory. If *output_filepath* is given the result
    is moved there afterwards.

    Parameters
    ----------
    dsb_filepath : str
        Path to the input .dsb file.
    output_filepath : str, optional
        Desired output .xml path.  When omitted the XML is placed
        next to the .dsb with the same stem name.
    exe_path : str, optional
        Explicit path to DesignBuilder.exe.
    timeout : float
        Maximum seconds to wait for the output file (default 120).

    Returns
    -------
    Path
        Path to the created .xml file.
    """
    dsb_path = Path(dsb_filepath).resolve()
    if not dsb_path.is_file():
        raise FileNotFoundError(f"DSB file not found: {dsb_path}")
    if dsb_path.suffix.lower() != ".dsb":
        raise ValueError(f"Expected a .dsb file, got: {dsb_path.suffix}")

    # DesignBuilder writes <stem>.xml next to the .dsb
    expected_xml = dsb_path.with_suffix(".xml")

    handle = run_async(dsb_path, export_xml(), exe_path=exe_path)
    try:
        found = _wait_for_file(expected_xml, timeout=timeout)
    finally:
        # Always kill DesignBuilder — it won't exit on its own
        kill_process()

    if not found:
        raise FileNotFoundError(
            f"DesignBuilder did not produce the expected output "
            f"within {timeout}s: {expected_xml}"
        )

    # Move to desired location if requested
    if output_filepath:
        dest = Path(output_filepath).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(expected_xml), str(dest))
        print(f"Exported: {dest}")
        return dest

    print(f"Exported: {expected_xml}")
    return expected_xml


def xml_to_dsb(
    xml_filepath: str,
    output_filepath: Optional[str] = None,
    exe_path: Optional[str] = None,
    timeout: float = 120,
) -> Path:
    """[NOT WORKING] Convert a .xml (dbXML) file to .dsb using DesignBuilder CLI.

    WARNING: DesignBuilder does not currently support XML import via command line.
    This function will cause an automation error in DesignBuilder.

    Calls: DesignBuilder <file.xml>

    Note: When DesignBuilder opens an XML it imports the model and
    creates a .dsb with a " 1" suffix (e.g. Shoebox.xml -> Shoebox 1.dsb).
    Unlike export, the .dsb is only written to disk once DesignBuilder
    finishes its import work.  This function uses ``kill_when_idle`` to
    let DB complete processing before terminating it.

    Parameters
    ----------
    xml_filepath : str
        Path to the input .xml file.
    output_filepath : str, optional
        Desired output .dsb path.  When omitted the function returns
        whichever .dsb DesignBuilder created.
    exe_path : str, optional
        Explicit path to DesignBuilder.exe.
    timeout : float
        Maximum seconds to wait for idle detection (default 120).
        This is used as the startup grace period.

    Returns
    -------
    Path
        Path to the created .dsb file.
    """
    xml_path = Path(xml_filepath).resolve()
    if not xml_path.is_file():
        raise FileNotFoundError(f"XML file not found: {xml_path}")
    if xml_path.suffix.lower() != ".xml":
        raise ValueError(f"Expected a .xml file, got: {xml_path.suffix}")

    # Track existing .dsb files so we can detect the new one
    parent = xml_path.parent
    existing_dsbs = set(parent.glob("*.dsb"))

    # XML import: no /process= needed, just open the file.
    # DB writes the .dsb once its import work is done, so we let it
    # run until CPU goes idle, then kill it.
    handle = run_async(xml_path, exe_path=exe_path)
    try:
        kill_when_idle(startup_period=timeout)
    except Exception:
        kill_process()

    # Small delay to let the filesystem flush after process exit
    time.sleep(1)

    created_dsb = _find_new_dsb(parent, existing_dsbs, xml_path.stem)

    if created_dsb is None:
        raise FileNotFoundError(
            f"DesignBuilder did not produce a .dsb file in: {parent}"
        )

    # Move to desired location if requested
    if output_filepath:
        dest = Path(output_filepath).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(created_dsb), str(dest))
        print(f"Imported: {dest}")
        return dest

    print(f"Imported: {created_dsb}")
    return created_dsb
