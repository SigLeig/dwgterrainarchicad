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

### Download and install locally

If you do not use Git, download this branch as a ZIP file:

```text
https://github.com/SigLeig/dwgterrainarchicad/archive/refs/heads/cursor/step-ifc-converter-2003.zip
```

Unzip it, open a terminal in the extracted folder, then run the installer for
your operating system.

macOS/Linux:

```bash
./install-local.sh
```

Windows PowerShell:

```powershell
.\install-local.ps1
```

If you use Git:

```bash
git clone https://github.com/SigLeig/dwgterrainarchicad.git
cd dwgterrainarchicad
git checkout cursor/step-ifc-converter-2003
./install-local.sh
```

Manual Python install:

```bash
python3 -m pip install --user -e .
```

### Usage

Convert a STEP file to IFC:

```bash
step-to-ifc model.step model.ifc
```

You can also run the local launcher directly from the repository without
installing first:

```bash
./step-to-ifc model.step model.ifc
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
