"""
xml_utils.py
====================================
Lightweight XML helpers for db_cli.

These were originally imported from ``designbuilder_schema.utils`` but the
schema package (now ``db_schema``) no longer ships them, so db_cli carries
its own ElementTree-based implementations.
"""

import xml.etree.ElementTree as ET


def file_to_dict(filepath) -> dict:
    """Parse an XML file into ``{root_tag: {attr: value, ...}}``.

    Only the root element's tag and attributes are captured, which is all
    the CLI needs (e.g. reading the ``version`` attribute of ``dsbXML``).
    Raises on malformed or missing files, matching the behaviour that
    ``db_cli.cli.get_version`` wraps in a RuntimeError.
    """
    root = ET.parse(filepath).getroot()
    return {root.tag: dict(root.attrib)}


def dict_to_file(dictionary: dict, filepath) -> None:
    """Write ``{root_tag: {attr: value, ...}}`` back to an XML file.

    Inverse of :func:`file_to_dict`: the single top-level key becomes the
    root element's tag and its mapping becomes the root attributes
    (values are stringified). Raises ValueError if the dictionary does not
    contain exactly one root entry.
    """
    if len(dictionary) != 1:
        raise ValueError(
            f"Expected a single root entry, got {len(dictionary)}: "
            f"{list(dictionary.keys())}"
        )
    (root_tag, attributes), = dictionary.items()
    root = ET.Element(root_tag, {k: str(v) for k, v in attributes.items()})
    ET.ElementTree(root).write(filepath, encoding="unicode", xml_declaration=True)
