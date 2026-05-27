# Double-click or run this file in PowerShell to open the visual area selector.
#
# It opens a small window where you can:
# 1. choose the DXF file
# 2. click "Vis tegning"
# 3. drag a rectangle around the area you want
# 4. click "Eksporter valgt omrade"

py -m pip install --upgrade git+https://github.com/SigLeig/dwgterrainarchicad.git@cursor/dwg-to-archicad-terrain-b866
py -m dwgterrainarchicad.gui
