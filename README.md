# Dwarf Fortress Screenshot to Map Tool

Stitches together a set of overlapping screenshots of a Dwarf Fortress embark at a given elevation,
identifies the underground sections,
and creates a very basic ODS spreadsheet showing the diggable areas.
Add some conditional formatting to the spreadsheet to color the diggable and undiggable areas with different colors,
and you're one step closer to being able to plan your digs in advance.

## Installation

`pip install -r requirements.txt`

## In Dwarf Fortress

Ideally, right after you start a new embark,
pause the game,
zoom as far out as you can, and
give digging orders for three tiles in the extreme northwest of the embark area:

```
dd...
d....
.....
.....
.....
```

Also seen in `templates/registration-mark.png`:

![templates/registration-mark.png](templates/registration-mark.png)

This gives the tool a registration mark to know where the embark begins. 
Otherwise it won't know the right crop boundary for the images.

## Screenshots folder

Organize your screenshots in this folder by world name and elevation, for example: `screenshots/Nitom Gomath/35/*.png` for all screenshots taken of *Nitom Gomath* at elevation 35.
It shouldn't matter what the files are named, as long as they're PNG files:
I'm using Greenshot to take screenshots, and the default filenames it used worked fine.

On initial testing (2560x1440 monitor, running in maximized windowed mode),
I can zoom all the way out and capture a 4x4 embark area with 6 screenshots 
(making three rows of two screenshots each with a lot of overlap in the horizontal direction).

## Running

`python df-screenshot-to-map.py`

## Examples

See the `examples` folder for some screenshots and a slightly modified ODS spreadsheet with conditional formatting.

## TODO:

- Iterate over the elevation folders, creating a new sheet in the ODS file for each elevation.
- Set a better column width and conditional formatting to the ODS file.