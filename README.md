# db-cli

Command line interface for [DesignBuilder](https://designbuilder.co.uk/) file operations. Convert between `.dsb`, `.xml`, and `.json` formats, validate files against the DesignBuilder schema, and inspect schema versions.

## Installation

```bash
pip install git+https://github.com/DesignBuilderSoftware/db-cli
```

## Commands

| Command | Description |
|---------|-------------|
| `version <file>` | Show the dsbXML schema version of a file |
| `validate <file>` | Validate a file against the DesignBuilder schema |
| `xml2json <file>` | Convert a DesignBuilder XML file to JSON |
| `json2xml <file>` | Convert a DesignBuilder JSON file to XML |
| `dsb2xml <file> [--output <path>] [--exe <path>]` | Export a `.dsb` file to XML using DesignBuilder |
| `close` | Close any running DesignBuilder process |

## Usage

```bash
# Inspect schema version
db-cli version Shoebox261.xml

# Validate against schema
db-cli validate Shoebox261.xml

# Convert between XML and JSON
db-cli xml2json Shoebox261.xml
db-cli json2xml Shoebox261.json

# Export .dsb to XML (requires DesignBuilder installed)
db-cli dsb2xml Shoebox261.dsb
db-cli dsb2xml Shoebox261.dsb --output exported.xml --exe "C:\Program Files\DesignBuilder\DesignBuilder.exe"

# Close DesignBuilder process
db-cli close
```

## Requirements

- Python 3
- [DesignBuilder](https://designbuilder.co.uk/) installation (only required for `dsb2xml` and `close` commands)

## Dependencies

- [fire](https://github.com/google/python-fire) — CLI generation
- [designbuilder_schema](https://github.com/Tokarzewski/designbuilder_schema) — schema validation and conversion utilities
- [db-process](https://github.com/DesignBuilderSoftware/db-process) — DesignBuilder process management
