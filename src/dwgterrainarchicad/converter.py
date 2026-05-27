from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path


class ConversionError(RuntimeError):
    """Raised when a DWG file cannot be converted to DXF."""


def ensure_dxf(
    input_path: Path,
    work_dir: Path,
    converter: str | None = None,
) -> Path:
    """Return a DXF path, converting DWG input when needed."""

    suffix = input_path.suffix.lower()
    if suffix == ".dxf":
        return input_path
    if suffix != ".dwg":
        raise ConversionError(f"Unsupported input format: {input_path.suffix}")

    work_dir.mkdir(parents=True, exist_ok=True)
    if converter:
        return _run_user_converter(input_path, work_dir, converter)

    oda = _which_any("ODAFileConverter", "ODAFileConverter.exe", "TeighaFileConverter")
    if oda:
        return _run_oda_converter(input_path, work_dir, oda)

    dwgread = shutil.which("dwgread")
    if dwgread:
        return _run_dwgread(input_path, work_dir, dwgread)

    raise ConversionError(
        "DWG input requires an external converter. Install ODA File Converter "
        "or LibreDWG's dwgread, convert the file to DXF manually, or pass "
        "--converter with a command containing {input} and {output} placeholders."
    )


def _which_any(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _run_oda_converter(input_path: Path, work_dir: Path, executable: str) -> Path:
    command = [
        executable,
        str(input_path.parent),
        str(work_dir),
        "ACAD2018",
        "DXF",
        "0",
        "1",
        input_path.name,
    ]
    _run(command, "ODA File Converter")
    return _find_converted_dxf(input_path, work_dir)


def _run_dwgread(input_path: Path, work_dir: Path, executable: str) -> Path:
    output_path = work_dir / f"{input_path.stem}.dxf"
    command = [
        executable,
        "-O",
        "DXF",
        "-o",
        str(output_path),
        str(input_path),
    ]
    _run(command, "dwgread")
    if not output_path.exists():
        raise ConversionError(f"dwgread completed but did not create {output_path}")
    return output_path


def _run_user_converter(input_path: Path, work_dir: Path, converter: str) -> Path:
    output_path = work_dir / f"{input_path.stem}.dxf"

    if "{input}" in converter or "{output}" in converter:
        command = shlex.split(
            converter.format(input=str(input_path), output=str(output_path))
        )
    else:
        parts = shlex.split(converter)
        executable_name = Path(parts[0]).name.lower()
        if "odafileconverter" in executable_name or "teighafileconverter" in executable_name:
            command = [
                *parts,
                str(input_path.parent),
                str(work_dir),
                "ACAD2018",
                "DXF",
                "0",
                "1",
                input_path.name,
            ]
        else:
            command = [*parts, str(input_path), str(output_path)]

    _run(command, "custom converter")
    if output_path.exists():
        return output_path
    return _find_converted_dxf(input_path, work_dir)


def _find_converted_dxf(input_path: Path, work_dir: Path) -> Path:
    expected = work_dir / f"{input_path.stem}.dxf"
    if expected.exists():
        return expected

    lower_stem = input_path.stem.lower()
    matches = [
        path
        for path in work_dir.glob("*.dxf")
        if path.stem.lower() == lower_stem
    ]
    if matches:
        return matches[0]

    raise ConversionError(
        f"Converter completed but no DXF matching {input_path.name} was found in {work_dir}"
    )


def _run(command: list[str], label: str) -> None:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ConversionError(f"{label} was not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        output = stderr or stdout or f"exit code {exc.returncode}"
        raise ConversionError(f"{label} failed: {output}") from exc

    if completed.stderr.strip():
        # Some converters report non-fatal diagnostics on stderr; keep the run successful.
        return
