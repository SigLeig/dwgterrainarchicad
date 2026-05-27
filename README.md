# dwgterrainarchicad

Small Python CLI for turning DWG/DXF terrain data into files that are easy to
import into Archicad as a terrain mesh.

The practical workflow is:

1. Convert DWG to DXF when the source is a DWG file.
2. Extract elevated CAD entities such as contour polylines, 3D polylines,
   survey points, lines, arcs, splines, and 3DFACE vertices.
3. Write a tab-separated `X Y Z` text file for Archicad's surveyor/mesh import,
   plus CSV and metadata files for inspection.

DWG is a proprietary binary format, so the tool intentionally does not pretend
to parse DWG directly. It reads DXF directly with `ezdxf`, and it can call an
installed converter for DWG input.

## Install

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[test]"
pytest
```

## DWG conversion prerequisites

For `.dwg` files, install one of these locally:

- ODA File Converter
- LibreDWG `dwgread`
- another converter command you can pass with `--converter`

If you already have a `.dxf`, no converter is needed.

## Example

PowerShell example for the file path in the original request:

```powershell
dwg-terrain-archicad `
  "C:\Users\Sigmund\Downloads\Filemail.com - Bordalen\t_fkb_borddalen_utm32.dwg" `
  --output-dir ".\borddalen-terrain" `
  --sample-distance 2 `
  --layers "KOTE*,TERRAIN*,HOYDE*"
```

If ODA File Converter is installed but not on `PATH`, pass the executable path:

```powershell
dwg-terrain-archicad `
  "C:\Users\Sigmund\Downloads\Filemail.com - Bordalen\t_fkb_borddalen_utm32.dwg" `
  --converter "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe" `
  --output-dir ".\borddalen-terrain"
```

For a DXF file:

```bash
dwg-terrain-archicad terrain.dxf --output-dir terrain-output --sample-distance 1
```

## Outputs

For an input named `terrain.dwg`, the output directory contains:

- `terrain_archicad_surveyor.txt` - tab-separated `X Y Z`, no header
- `terrain_points.csv` - same points with source entity and layer columns
- `terrain_metadata.json` - source path, origin offset, bounds, entity counts

By default, zero-elevation points are skipped because many map DWGs contain 2D
plan data at `Z=0` that should not become part of the terrain. Use
`--include-zero-elevation` if your terrain really contains zero elevation.

Large UTM coordinates are shifted near local origin by default (`--origin auto`)
to avoid placing the Archicad model far from project origin. The original offset
is saved in the metadata file. Use `--origin none` if you need unshifted world
coordinates.

## Limit the converted area

Large map files can create millions of points. Use `--bbox` to export only one
rectangle from the original DWG/DXF coordinates:

```powershell
py -m dwgterrainarchicad `
  "C:\Users\Sigmund\Downloads\Filemail.com - Bordalen\Output\t_fkb_borddalen_utm32.dxf" `
  --output-dir "C:\Users\Sigmund\Downloads\borddalen-terrain-small" `
  --sample-distance 20 `
  --include-zero-elevation `
  --bbox "355500,6636500,355900,6636900"
```

The order is:

```text
min X, min Y, max X, max Y
```

For UTM map files these numbers are meters. You can also edit
`run_borddalen.ps1` and fill in `$MinX`, `$MinY`, `$MaxX`, and `$MaxY` near the
top of the file.

## Import into Archicad

1. Run the converter and open the generated output directory.
2. In Archicad, use the command for creating a mesh from surveyor data
   (menu names vary by Archicad version, commonly under File > Interoperability).
3. Select `*_archicad_surveyor.txt`.
4. Choose tab/space separated columns in `X Y Z` order and the same unit as the
   DWG/DXF, typically meters for UTM data.
5. If you used the default origin shift, keep the mesh near project origin and
   use the metadata origin if you need to document the original UTM placement.

## Useful options

```bash
dwg-terrain-archicad --help
```

- `--layers "KOTE*,TERRAIN*"` limits extraction to contour/terrain layers.
- `--sample-distance 2` densifies contour lines every 2 drawing units.
- `--min-z` and `--max-z` remove outlier elevations.
- `--origin min`, `--origin none`, or `--origin X,Y` control coordinate shifting.
