import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from step_to_ifc.cli import (
    _find_freecadcmd,
    _prepend_pythonpath,
    _run_with_freecadcmd,
    _validate_paths,
)
from step_to_ifc.rotations import RotationStep


class CliTests(unittest.TestCase):
    def test_validate_paths_accepts_step_to_ifc(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            step_file = Path(temp_dir) / "model.step"
            step_file.write_text("ISO-10303-21;", encoding="utf-8")

            _validate_paths(step_file, Path(temp_dir) / "model.ifc")

    def test_validate_paths_rejects_wrong_input_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "model.obj"
            input_file.write_text("obj", encoding="utf-8")

            with self.assertRaises(RuntimeError):
                _validate_paths(input_file, Path(temp_dir) / "model.ifc")

    def test_validate_paths_rejects_wrong_output_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            step_file = Path(temp_dir) / "model.stp"
            step_file.write_text("ISO-10303-21;", encoding="utf-8")

            with self.assertRaises(RuntimeError):
                _validate_paths(step_file, Path(temp_dir) / "model.obj")

    def test_find_freecadcmd_prefers_explicit_command(self):
        self.assertEqual(_find_freecadcmd("/opt/freecad/FreeCADCmd"), "/opt/freecad/FreeCADCmd")

    def test_prepend_pythonpath(self):
        self.assertEqual(_prepend_pythonpath(Path("/src"), None), "/src")
        self.assertEqual(
            _prepend_pythonpath(Path("/src"), "/existing"),
            f"/src{os.pathsep}/existing",
        )

    @mock.patch("step_to_ifc.cli.subprocess.run")
    def test_freecadcmd_invocation_contains_repeated_rotations(self, run_mock):
        run_mock.return_value.returncode = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            step_file = Path(temp_dir) / "model.step"
            ifc_file = Path(temp_dir) / "model.ifc"
            step_file.write_text("ISO-10303-21;", encoding="utf-8")

            result = _run_with_freecadcmd(
                input_step=step_file,
                output_ifc=ifc_file,
                rotations=[RotationStep("x", 90), RotationStep("z", -90)],
                freecad_cmd="/usr/bin/FreeCADCmd",
            )

        self.assertEqual(result, 0)
        command = run_mock.call_args.args[0]
        self.assertEqual(command[0], "/usr/bin/FreeCADCmd")
        self.assertIn("--input", command)
        self.assertIn("--output", command)
        self.assertEqual(command.count("--rotate"), 2)
        self.assertIn("x+", command)
        self.assertIn("z-", command)


if __name__ == "__main__":
    unittest.main()
