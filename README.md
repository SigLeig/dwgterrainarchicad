# dwgterrainarchicad

Utilities for CAD/BIM terrain and model conversion workflows.

## STEP to IFC converter

This repository includes a command line program that converts `.step`/`.stp`
files to `.ifc` files and can rotate the model in 90 degree steps before export.
It uses FreeCAD for the actual CAD geometry import/export.

### Requirements

- Python 3.9+
- FreeCAD with IFC/BIM export support (`FreeCADCmd` available on `PATH`)

If `FreeCADCmd` is installed in a non-standard location, pass `--freecad-cmd` or
set `STEP_TO_IFC_FREECAD_CMD=/path/to/FreeCADCmd`.

### Install locally

```bash
python3 -m pip install -e .
```

### Usage

Convert a STEP file to IFC:

```bash
step-to-ifc model.step model.ifc
```

If the output path is omitted, the converter writes beside the input with the
same filename and an `.ifc` extension:

```bash
step-to-ifc model.step
```

Rotate the model 90 degrees before export:

```bash
step-to-ifc model.step model.ifc --rotate x+
```

Rotations can be combined and are applied in the order they are provided:

```bash
step-to-ifc model.step model.ifc --rotate x+ --rotate y- --rotate z+
```

Supported 90 degree directions:

- `x+` / `x-`
- `y+` / `y-`
- `z+` / `z-`

The parser also accepts equivalent forms such as `x:90`, `y=-90` and `+z`.

### Run tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```
