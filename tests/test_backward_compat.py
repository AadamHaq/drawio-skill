#!/usr/bin/env python3
"""Backward compatibility regression tests for layout.py.

Verifies that ALL existing layout.py commands produce unchanged output for known inputs.
These are the pre-feature expected values — any deviation indicates a regression.
"""

import os
import subprocess
import unittest

LAYOUT_PY = os.path.join(
    os.path.dirname(__file__), "..", "claude", "skills", "diagram", "layout.py"
)


def run_layout(*args):
    """Run layout.py with given args and return CompletedProcess."""
    return subprocess.run(
        ["python3", LAYOUT_PY] + list(args),
        capture_output=True,
        text=True,
    )


def parse_output(stdout):
    """Parse key=value pairs from stdout into a dict.

    Handles lines like:
      - "sw_w=316"
      - "container_x=12  container_y=45  container_w=292"
      - "split_y=265  (rel to swimlane)"
      - "step[0]: y=45  h=40  (lines=1)"
    """
    result = {}
    for line in stdout.strip().splitlines():
        for part in line.split():
            if "=" in part:
                key, val = part.split("=", 1)
                result[key] = val
    return result


class TestBackwardCompatSwimlanes(unittest.TestCase):
    """Regression: swimlanes 2 → sw_w=316, step_w=280, total_w=658, first_sl_x=84."""

    def test_swimlanes_2(self):
        result = run_layout("swimlanes", "2")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["sw_w"], "316")
        self.assertEqual(out["step_w"], "280")
        self.assertEqual(out["total_w"], "658")
        self.assertEqual(out["first_sl_x"], "84")


class TestBackwardCompatInputs(unittest.TestCase):
    """Regression: inputs 3 → total_w=520, first_x=153."""

    def test_inputs_3(self):
        result = run_layout("inputs", "3")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["total_w"], "520")
        self.assertEqual(out["first_x"], "153")


class TestBackwardCompatSteps(unittest.TestCase):
    """Regression: steps 316 30 1 2 1 → first_step_y=45, step[0] y=45 h=40, step[1] y=101 h=58, step[2] y=175 h=40."""

    def test_steps_316_30_1_2_1(self):
        result = run_layout("steps", "316", "30", "1", "2", "1")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        # first_step_y is output as "first_step_y=45" (with trailing context)
        self.assertEqual(out["first_step_y"], "45")
        # Parse per-step values from lines like "step[0]: y=45  h=40  (lines=1)"
        lines = result.stdout.strip().splitlines()
        step_data = {}
        for line in lines:
            if line.startswith("step["):
                parts = {}
                for token in line.split():
                    if "=" in token:
                        k, v = token.split("=", 1)
                        parts[k] = v
                # Extract step index from "step[N]:"
                idx = line.split("]")[0].split("[")[1]
                step_data[idx] = parts

        self.assertEqual(step_data["0"]["y"], "45")
        self.assertEqual(step_data["0"]["h"], "40")
        self.assertEqual(step_data["1"]["y"], "101")
        self.assertEqual(step_data["1"]["h"], "58")
        self.assertEqual(step_data["2"]["y"], "175")
        self.assertEqual(step_data["2"]["h"], "40")


class TestBackwardCompatSplit(unittest.TestCase):
    """Regression: split 316 175 40 → split_y=265, pass_x=18, pass_w=135, fail_x=163, fail_w=135, sl_height=321."""

    def test_split_316_175_40(self):
        result = run_layout("split", "316", "175", "40")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["split_y"], "265")
        self.assertEqual(out["pass_x"], "18")
        self.assertEqual(out["pass_w"], "135")
        self.assertEqual(out["fail_x"], "163")
        self.assertEqual(out["fail_w"], "135")
        self.assertEqual(out["sl_height"], "321")


class TestBackwardCompatCheckApproach(unittest.TestCase):
    """Regression: check-approach 200 400 300 500 200 100 0.5 0 → OK."""

    def test_check_approach_ok(self):
        result = run_layout("check-approach", "200", "400", "300", "500", "200", "100", "0.5", "0")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "OK")


class TestBackwardCompatNestedContainer(unittest.TestCase):
    """Regression: nested-container 316 45 3 1 2 1 → container_w=292, child_step_w=256, container_h=210."""

    def test_nested_container_316_45_3(self):
        result = run_layout("nested-container", "316", "45", "3", "1", "2", "1")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["container_w"], "292")
        self.assertEqual(out["child_step_w"], "256")
        self.assertEqual(out["container_h"], "210")


class TestBackwardCompatLoopAnnotation(unittest.TestCase):
    """Regression: loop-annotation 45 200 58 316 → annotation_x=4, annotation_w=308."""

    def test_loop_annotation_45_200_58_316(self):
        result = run_layout("loop-annotation", "45", "200", "58", "316")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["annotation_x"], "4")
        self.assertEqual(out["annotation_w"], "308")


class TestBackwardCompatNSplit(unittest.TestCase):
    """Regression: n-split 316 200 40 3 50 → split_y=290, sl_height=346."""

    def test_n_split_316_200_40_3_50(self):
        result = run_layout("n-split", "316", "200", "40", "3", "50")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["split_y"], "290")
        self.assertEqual(out["sl_height"], "346")


class TestBackwardCompatMultipageOverview(unittest.TestCase):
    """Regression: multipage overview → page_w=827, page_h=1169, orientation=portrait."""

    def test_multipage_overview(self):
        result = run_layout("multipage", "overview")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["page_w"], "827")
        self.assertEqual(out["page_h"], "1169")
        self.assertEqual(out["orientation"], "portrait")


class TestBackwardCompatMultipageDrillDown(unittest.TestCase):
    """Regression: multipage drill_down 5 → page_w=1169, page_h=827, orientation=landscape."""

    def test_multipage_drill_down_5(self):
        result = run_layout("multipage", "drill_down", "5")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["page_w"], "1169")
        self.assertEqual(out["page_h"], "827")
        self.assertEqual(out["orientation"], "landscape")


if __name__ == "__main__":
    unittest.main()
