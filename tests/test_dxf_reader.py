from pathlib import Path

import ezdxf

from dwgterrainarchicad.dxf_reader import ReadOptions, read_terrain_points


def _write_sample_dxf(path: Path) -> None:
    doc = ezdxf.new("R2018")
    modelspace = doc.modelspace()
    modelspace.add_lwpolyline(
        [(500_000, 6_700_000), (500_010, 6_700_000), (500_010, 6_700_010)],
        dxfattribs={"layer": "KOTER", "elevation": 42.0},
    )
    modelspace.add_point((0, 0, 0), dxfattribs={"layer": "NOT_TERRAIN"})
    doc.saveas(path)


def test_reads_and_samples_elevated_contours(tmp_path: Path) -> None:
    dxf_path = tmp_path / "terrain.dxf"
    _write_sample_dxf(dxf_path)

    result = read_terrain_points(
        dxf_path,
        ReadOptions(layers=("KOTER",), sample_distance=5.0),
    )

    assert len(result.points) == 5
    assert {point.z for point in result.points} == {42.0}
    assert result.report.points_before_dedupe == 5
    assert result.report.points_after_dedupe == 5


def test_skips_zero_elevation_by_default(tmp_path: Path) -> None:
    dxf_path = tmp_path / "zero.dxf"
    doc = ezdxf.new("R2018")
    doc.modelspace().add_point((1, 2, 0), dxfattribs={"layer": "SURVEY"})
    doc.saveas(dxf_path)

    result = read_terrain_points(dxf_path, ReadOptions())

    assert result.points == []
    assert result.report.skipped_zero_elevation == 1



def test_bbox_limits_exported_area(tmp_path: Path) -> None:
    dxf_path = tmp_path / "terrain.dxf"
    _write_sample_dxf(dxf_path)

    result = read_terrain_points(
        dxf_path,
        ReadOptions(
            layers=("KOTER",),
            bbox=(500_000, 6_700_000, 500_005, 6_700_001),
            sample_distance=5.0,
        ),
    )

    assert [(point.x, point.y, point.z) for point in result.points] == [
        (500_000, 6_700_000, 42.0),
        (500_005, 6_700_000, 42.0),
    ]
    assert result.report.skipped_bbox == 3
