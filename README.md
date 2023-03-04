# Dwarf Fortress Elevations to Map Tool

Reads a series of text files for each elevation of a Dwarf Fortress embark,
identifies the underground sections,
and creates an Excel workbook showing the diggable areas with one worksheet per elevation.
The workbook will have conditional formatting applied allowing you to copy/paste different values in the underground regions
(0 is white, 1 is black, and values outside that range will be uncolored).

This is a much better method than my first attempt that did a lot of image processing of screenshots, but does require use of [DFHack](https://docs.dfhack.org/) to create the text files.

[![Original minimap](embark-elevation-df-thumbnail.png)](embark-elevation-df.png)

[![Corresponding worksheet from an Excel workbook](embark-elevation-excel-thumbnail.png)](embark-elevation-excel.png)

## Installation

### Python script

`pip install -r requirements.txt`

Currently uses:

- openpyxl

### DFHack and Lua script

See [Installing DFHack](https://docs.dfhack.org/en/stable/docs/Installing.html) for instructions on how to install DFHack.

Copy `export-diggable-areas.lua` to the DFHack scripts folder (in the Steam version, that's `Dwarf Fortress/hack/scripts`).

## In Dwarf Fortress

Ideally, right after you start a new embark with DFHack enabled,
pause the game and run `export-diggable-areas` in DFHack.
By default, `export-diggable-areas` will not show any fully subterranean elevations to reduce spoilers.
Run it as `export-diggable-areas spoilers` (or any other parameter) to get exports from all elevations.

## Elevations folder

Organize your text export files in this folder by world name, for example: `elevations/Mineally/elevation-*.txt` for all text files from the *Mineally* embark.

## Running

`python df-screenshot-to-map.py --help` for help. Currently shows:

```
usage: df-screenshot-to-map.py [-h] [--basedir BASEDIR] [--zoom ZOOM]
                               [--embark-elevation EMBARK_ELEVATION]
                               world

positional arguments:
  world                 Folder in basedir containing minimap screenshots

options:
  -h, --help            show this help message and exit
  --basedir BASEDIR     Base directory containing folders with minimap elevations (defaults to
                        'elevations')
  --zoom ZOOM           Spreadsheet zoom level (in percent, defaults to 25)
  --embark-elevation EMBARK_ELEVATION
                        Elevation of embark site (if specified, will set active sheet in Excel workbook)
```

For example, if you use the deafult text files in the `examples/elevations/Mineally` folder:

`python .\df-screenshot-to-map.py --basedir examples/elevations Mineally --embark-elevation 36`

Or if you copy them to the `elevations` folder:

`python .\df-screenshot-to-map.py Mineally --embark-elevation 36`

## Examples

See the `examples` folder for some elevation files and resulting spreadsheet.

## TODO:

- Remove default 'Sheet' worksheet from workbook.
