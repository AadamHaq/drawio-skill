#!/usr/bin/env python3
"""Unit tests for layout.py new commands: nested-container, loop-annotation, n-split, multipage.

Tests run layout.py as a subprocess and check stdout/stderr/exit codes.
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
    """Parse key=value lines from stdout into a dict."""
    result = {}
    for line in stdout.strip().splitlines():
        # Handle lines like "container_x=12  container_y=45  container_w=292"
        for part in line.split():
            if "=" in part:
                key, val = part.split("=", 1)
                result[key] = val
    return result


class TestNestedContainer(unittest.TestCase):
    """Tests for the nested-container command."""

    def test_basic_3_children(self):
        """Test with parent_sw_w=316, parent_start_y=45, n_children=3, lines=[1, 2, 1]."""
        result = run_layout("nested-container", "316", "45", "3", "1", "2", "1")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["container_w"], "292")
        self.assertEqual(out["child_step_w"], "256")

    def test_minimum_width(self):
        """Test with parent_sw_w=100 (minimum allowed)."""
        result = run_layout("nested-container", "100", "10", "1", "1")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        # container_w = 100 - 24 = 76
        self.assertEqual(out["container_w"], "76")
        # child_step_w = 100 - 60 = 40
        self.assertEqual(out["child_step_w"], "40")

    def test_too_small_width_error(self):
        """Test with parent_sw_w=50 → error."""
        result = run_layout("nested-container", "50", "10", "1", "1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("error", result.stderr.lower())

    def test_insufficient_line_args(self):
        """Test with fewer line args than n_children → error."""
        result = run_layout("nested-container", "316", "45", "3", "1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage", result.stderr.lower())


class TestLoopAnnotation(unittest.TestCase):
    """Tests for the loop-annotation command."""

    def test_basic(self):
        """Test with 45 200 58 316 → annotation_x=4, annotation_w=308."""
        result = run_layout("loop-annotation", "45", "200", "58", "316")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["annotation_x"], "4")
        self.assertEqual(out["annotation_w"], "308")  # 316 - 8

    def test_single_node(self):
        """Test where first_node_y == last_node_y (single node)."""
        result = run_layout("loop-annotation", "100", "100", "40", "200")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        # annotation_y = 100 - 15 - 20 = 65
        self.assertEqual(out["annotation_y"], "65")
        # annotation_h = (100 + 40 + 15) - 65 = 90
        self.assertEqual(out["annotation_h"], "90")

    def test_zero_arg_error(self):
        """Test with zero/negative args → error."""
        result = run_layout("loop-annotation", "0", "200", "58", "316")
        self.assertEqual(result.returncode, 1)
        self.assertIn("positive integers", result.stderr.lower())

    def test_negative_arg_error(self):
        """Test with negative arg → error."""
        result = run_layout("loop-annotation", "45", "-10", "58", "316")
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage", result.stderr.lower())


class TestNSplit(unittest.TestCase):
    """Tests for the n-split command."""

    def test_2_outcomes(self):
        """Test with 2 outcomes → verify 2 boxes."""
        result = run_layout("n-split", "316", "200", "40", "2")
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().splitlines()
        outcome_lines = [l for l in lines if l.startswith("outcome[")]
        self.assertEqual(len(outcome_lines), 2)

    def test_3_outcomes(self):
        """Test with 316 200 40 3 50 → verify split_y=290, sl_height=346."""
        result = run_layout("n-split", "316", "200", "40", "3", "50")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        # split_y = 200 + 40 + 50 = 290
        self.assertEqual(out["split_y"], "290")
        # sl_height = 290 + 36 + 20 = 346
        self.assertEqual(out["sl_height"], "346")

    def test_5_outcomes_non_overlapping(self):
        """Test with 5 outcomes → verify all 5 boxes are non-overlapping."""
        result = run_layout("n-split", "316", "200", "40", "5")
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().splitlines()
        outcome_lines = [l for l in lines if l.startswith("outcome[")]
        self.assertEqual(len(outcome_lines), 5)
        # Parse x and w for each outcome
        boxes = []
        for line in outcome_lines:
            parts = parse_output(line)
            x = int(parts["x"])
            w = int(parts["w"])
            boxes.append((x, x + w))
        # Verify non-overlapping
        for i in range(len(boxes) - 1):
            self.assertLessEqual(boxes[i][1], boxes[i + 1][0],
                                 f"Box {i} overlaps with box {i+1}")

    def test_10_outcomes_fit(self):
        """Test with 10 outcomes → verify all boxes fit."""
        result = run_layout("n-split", "316", "200", "40", "10")
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().splitlines()
        outcome_lines = [l for l in lines if l.startswith("outcome[")]
        self.assertEqual(len(outcome_lines), 10)
        # All boxes should have positive width
        for line in outcome_lines:
            parts = parse_output(line)
            self.assertGreater(int(parts["w"]), 0)

    def test_1_outcome_error(self):
        """Test with 1 outcome → error (minimum is 2)."""
        result = run_layout("n-split", "316", "200", "40", "1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("n_outcomes must be >= 2", result.stderr)


class TestMultipage(unittest.TestCase):
    """Tests for the multipage command."""

    def test_overview(self):
        """Test overview → page_w=827, page_h=1169, orientation=portrait."""
        result = run_layout("multipage", "overview")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["page_w"], "827")
        self.assertEqual(out["page_h"], "1169")
        self.assertEqual(out["orientation"], "portrait")

    def test_drill_down_5_swimlanes(self):
        """Test drill_down with 5 swimlanes → landscape."""
        result = run_layout("multipage", "drill_down", "5")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["page_w"], "1169")
        self.assertEqual(out["page_h"], "827")
        self.assertEqual(out["orientation"], "landscape")

    def test_drill_down_2_swimlanes(self):
        """Test drill_down with 2 swimlanes → portrait."""
        result = run_layout("multipage", "drill_down", "2")
        self.assertEqual(result.returncode, 0)
        out = parse_output(result.stdout)
        self.assertEqual(out["page_w"], "827")
        self.assertEqual(out["page_h"], "1169")
        self.assertEqual(out["orientation"], "portrait")

    def test_invalid_type_error(self):
        """Test invalid page_type → error."""
        result = run_layout("multipage", "invalid_type")
        self.assertEqual(result.returncode, 1)
        self.assertIn("page_type must be one of", result.stderr)


if __name__ == "__main__":
    unittest.main()
