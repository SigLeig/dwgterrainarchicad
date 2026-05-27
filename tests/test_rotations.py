import unittest

from step_to_ifc.rotations import RotationStep, parse_rotation


class RotationParserTests(unittest.TestCase):
    def test_parses_direction_shortcuts(self):
        cases = {
            "x+": RotationStep("x", 90),
            "x-": RotationStep("x", -90),
            "+y": RotationStep("y", 90),
            "-z": RotationStep("z", -90),
            "X": RotationStep("x", 90),
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(parse_rotation(value), expected)

    def test_parses_axis_and_degrees(self):
        self.assertEqual(parse_rotation("x:90"), RotationStep("x", 90))
        self.assertEqual(parse_rotation("y=-90"), RotationStep("y", -90))
        self.assertEqual(parse_rotation("z90"), RotationStep("z", 90))

    def test_rejects_non_right_angle_rotation(self):
        with self.assertRaises(ValueError):
            parse_rotation("x:45")

    def test_rejects_unknown_axis(self):
        with self.assertRaises(ValueError):
            parse_rotation("a+")

    def test_cli_value_roundtrip(self):
        self.assertEqual(RotationStep("z", -90).cli_value(), "z-")


if __name__ == "__main__":
    unittest.main()
