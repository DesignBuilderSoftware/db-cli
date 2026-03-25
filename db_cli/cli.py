"""
cli.py
====================================
The command line interface for DesignBuilder file operations.
"""

import json
from pathlib import Path
from fire import Fire
from designbuilder_schema.utils import file_to_dict, load_model, dict_to_file
from db_cli.converter import dsb_to_xml as _dsb_to_xml
from db_cli.converter import xml_to_dsb as _xml_to_dsb
from db_process import kill_process


def get_version(filepath: str) -> str:
    """Return the schema version."""
    dictionary = file_to_dict(filepath)
    if "dsbJSON" in str(dictionary.keys()):
        return dictionary["dsbJSON"]["version"]
    elif "dsbXML" in str(dictionary.keys()):
        return dictionary["dsbXML"]["version"]
    else:
        print("Can't find dsbJSON or dsbXML in: ", dictionary.keys())


def xml_to_json(xml_filepath: str):
    """Convert XML file to JSON file."""
    dictionary = file_to_dict(xml_filepath)
    dictionary["dsbJSON"] = dictionary.pop("dsbXML")
    json_filepath = Path(xml_filepath).with_suffix(".json")

    with open(json_filepath, "w") as f:
        json.dump(dictionary, f, indent=4)


def json_to_xml(json_filepath: str):
    """Convert JSON file to XML file."""
    dictionary = file_to_dict(json_filepath)
    xml_filepath = str(Path(json_filepath).with_suffix(".xml"))
    dict_to_file(dictionary, xml_filepath)


def validate_file(filepath: str) -> str:
    """Check if file follows the schema."""
    model = load_model(filepath)
    return f"Validation successful, file saved in version {model.version}."


def dsb_to_xml(dsb_filepath: str, output: str = None, exe: str = None) -> str:
    """Convert .dsb file to .xml (dbXML) using DesignBuilder CLI.

    Calls DesignBuilder.exe with /process=miFExportAsXML.

    Args:
        dsb_filepath: Path to the input .dsb file.
        output: Optional output .xml path (default: same directory, same stem).
        exe: Optional path to DesignBuilder.exe (or set DESIGNBUILDER_EXE env var).
    """
    result = _dsb_to_xml(dsb_filepath, output_filepath=output, exe_path=exe)
    return f"Exported: {result}"


def xml_to_dsb(xml_filepath: str, output: str = None, exe: str = None) -> str:
    """[NOT WORKING] Convert .xml (dbXML) file to .dsb using DesignBuilder CLI.

    WARNING: DesignBuilder does not currently support XML import via command line.
    Running this command will cause an automation error in DesignBuilder.
    Kept here for future use when/if DesignBuilder adds CLI import support.

    Args:
        xml_filepath: Path to the input .xml file.
        output: Optional output .dsb path (default: auto-detected).
        exe: Optional path to DesignBuilder.exe (or set DESIGNBUILDER_EXE env var).
    """
    raise NotImplementedError(
        "xml2dsb is not working. DesignBuilder does not support XML import via command line."
    )


def close() -> str:
    """Close any running DesignBuilder process."""
    if kill_process():
        return "DesignBuilder process closed."
    return "No DesignBuilder process found."


def main():
    Fire(
        {
            "version": get_version,
            "validate": validate_file,
            "xml2json": xml_to_json,
            "json2xml": json_to_xml,
            "dsb2xml": dsb_to_xml,
            "xml2dsb": xml_to_dsb,
            "close": close,
        }
    )


if __name__ == "__main__":
    main()
