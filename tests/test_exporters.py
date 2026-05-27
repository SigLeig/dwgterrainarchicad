from pathlib import Path

from dwgterrainarchicad.dxf_reader import ExtractionReport
from dwgterrainarchicad.exporters import choose_origin, export_archicad_files
from dwgterrainarchicad.models import TerrainPoint


def test_auto_origin_shifts_large_utm_coordinates() -> None:
    points = [
        TerrainPoint(500_000, 6_700_000, 10),
        TerrainPoint(500_100, 6_700_050, 20),
    ]

    assert choose_origin(points, "auto") == (500_000, 6_700_000)


def test_exports_archicad_txt_csv_and_metadata(tmp_path: Path) -> None:
    points = [
        TerrainPoint(500_000, 6_700_000, 10, source="POINT", layer="SURVEY"),
        TerrainPoint(500_100, 6_700_050, 20, source="POINT", layer="SURVEY"),
    ]
    report = ExtractionReport(source_path=Path("terrain.dxf"))

    outputs = export_archicad_files(
        points,
        tmp_path,
        "terrain",
        origin=(500_000, 6_700_000),
        report=report,
    )

    assert outputs["archicad_txt"].read_text(encoding="utf-8").splitlines() == [
        "0.000\t0.000\t10.000",
        "100.000\t50.000\t20.000",
    ]
    assert outputs["csv"].exists()
    assert outputs["metadata"].exists()
