#!/usr/bin/env python3
"""Property-based test: Conditional Group Containment

**Validates: Requirements 5.1, 5.2, 5.3**

Property 8: For any set of 2+ service positions, verify:
1. The group bounding box contains all service positions:
   for each service (x, y, w, h), group_x <= x AND group_y <= y AND
   group_x + group_w >= x + w AND group_y + group_h >= y + h
2. group_w > 0 and group_h > 0
3. label_x is inside the group box: group_x <= label_x <= group_x + group_w
4. label_y is inside the group box: group_y <= label_y <= group_y + group_h
5. Padding is at least 20px: group_x <= min(x) - 20 and
   group_x + group_w >= max(x+w) + 20
"""

import os
import random
import re
import subprocess
import sys
import unittest

# Path to layout.py
LAYOUT_PY = os.path.join(
    os.path.dirname(__file__), "..", "claude", "skills", "diagram", "layout.py"
)


def run_conditional_group(positions):
    """Run layout.py conditional-group and return parsed output as a dict.

    Args:
        positions: list of tuples (x, y, w, h)

    Returns:
        dict with group_x, group_y, group_w, group_h, label_x, label_y
    """
    args = [
        sys.executable, LAYOUT_PY,
        "conditional-group",
    ] + [f"{x},{y},{w},{h}" for x, y, w, h in positions]

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"conditional-group failed (exit {result.returncode}): {result.stderr}"
        )

    output = result.stdout.strip()
    parsed = {}

    m = re.search(r"group_x=(-?\d+)", output)
    if m:
        parsed["group_x"] = int(m.group(1))
    m = re.search(r"group_y=(-?\d+)", output)
    if m:
        parsed["group_y"] = int(m.group(1))
    m = re.search(r"group_w=(-?\d+)", output)
    if m:
        parsed["group_w"] = int(m.group(1))
    m = re.search(r"group_h=(-?\d+)", output)
    if m:
        parsed["group_h"] = int(m.group(1))
    m = re.search(r"label_x=(-?\d+)", output)
    if m:
        parsed["label_x"] = int(m.group(1))
    m = re.search(r"label_y=(-?\d+)", output)
    if m:
        parsed["label_y"] = int(m.group(1))

    return parsed


class TestConditionalGroupContainment(unittest.TestCase):
    """Property 8: Conditional Group Containment

    For any set of 2+ service positions, verify structural invariants hold.
    """

    NUM_TRIALS = 80
    SEED = 42

    def setUp(self):
        self.rng = random.Random(self.SEED)

    def _generate_positions(self):
        """Generate 2-6 random service positions."""
        n = self.rng.randint(2, 6)
        positions = []
        for _ in range(n):
            x = self.rng.randint(40, 800)
            y = self.rng.randint(40, 600)
            w = self.rng.randint(100, 200)
            h = self.rng.randint(80, 150)
            positions.append((x, y, w, h))
        return positions

    def test_property_group_contains_all_services(self):
        """Property 8.1: Group bounding box contains all service positions."""
        for trial in range(self.NUM_TRIALS):
            positions = self._generate_positions()
            result = run_conditional_group(positions)

            group_x = result["group_x"]
            group_y = result["group_y"]
            group_w = result["group_w"]
            group_h = result["group_h"]

            for i, (x, y, w, h) in enumerate(positions):
                self.assertLessEqual(
                    group_x, x,
                    f"Trial {trial}: group_x ({group_x}) should be <= "
                    f"service[{i}].x ({x}), positions={positions}"
                )
                self.assertLessEqual(
                    group_y, y,
                    f"Trial {trial}: group_y ({group_y}) should be <= "
                    f"service[{i}].y ({y}), positions={positions}"
                )
                self.assertGreaterEqual(
                    group_x + group_w, x + w,
                    f"Trial {trial}: group_x+group_w ({group_x + group_w}) should be >= "
                    f"service[{i}].x+w ({x + w}), positions={positions}"
                )
                self.assertGreaterEqual(
                    group_y + group_h, y + h,
                    f"Trial {trial}: group_y+group_h ({group_y + group_h}) should be >= "
                    f"service[{i}].y+h ({y + h}), positions={positions}"
                )

    def test_property_group_dimensions_positive(self):
        """Property 8.2: group_w > 0 and group_h > 0."""
        for trial in range(self.NUM_TRIALS):
            positions = self._generate_positions()
            result = run_conditional_group(positions)

            self.assertGreater(
                result["group_w"], 0,
                f"Trial {trial}: group_w should be > 0, positions={positions}"
            )
            self.assertGreater(
                result["group_h"], 0,
                f"Trial {trial}: group_h should be > 0, positions={positions}"
            )

    def test_property_label_x_inside_group(self):
        """Property 8.3: label_x is inside the group box."""
        for trial in range(self.NUM_TRIALS):
            positions = self._generate_positions()
            result = run_conditional_group(positions)

            group_x = result["group_x"]
            group_w = result["group_w"]
            label_x = result["label_x"]

            self.assertGreaterEqual(
                label_x, group_x,
                f"Trial {trial}: label_x ({label_x}) should be >= "
                f"group_x ({group_x}), positions={positions}"
            )
            self.assertLessEqual(
                label_x, group_x + group_w,
                f"Trial {trial}: label_x ({label_x}) should be <= "
                f"group_x+group_w ({group_x + group_w}), positions={positions}"
            )

    def test_property_label_y_inside_group(self):
        """Property 8.4: label_y is inside the group box."""
        for trial in range(self.NUM_TRIALS):
            positions = self._generate_positions()
            result = run_conditional_group(positions)

            group_y = result["group_y"]
            group_h = result["group_h"]
            label_y = result["label_y"]

            self.assertGreaterEqual(
                label_y, group_y,
                f"Trial {trial}: label_y ({label_y}) should be >= "
                f"group_y ({group_y}), positions={positions}"
            )
            self.assertLessEqual(
                label_y, group_y + group_h,
                f"Trial {trial}: label_y ({label_y}) should be <= "
                f"group_y+group_h ({group_y + group_h}), positions={positions}"
            )

    def test_property_padding_at_least_20(self):
        """Property 8.5: Padding is at least 20px on all sides."""
        for trial in range(self.NUM_TRIALS):
            positions = self._generate_positions()
            result = run_conditional_group(positions)

            group_x = result["group_x"]
            group_y = result["group_y"]
            group_w = result["group_w"]
            group_h = result["group_h"]

            min_x = min(x for x, y, w, h in positions)
            max_right = max(x + w for x, y, w, h in positions)
            min_y = min(y for x, y, w, h in positions)
            max_bottom = max(y + h for x, y, w, h in positions)

            # Left padding
            self.assertLessEqual(
                group_x, min_x - 20,
                f"Trial {trial}: group_x ({group_x}) should be <= "
                f"min(x) - 20 ({min_x - 20}), positions={positions}"
            )
            # Right padding
            self.assertGreaterEqual(
                group_x + group_w, max_right + 20,
                f"Trial {trial}: group_x+group_w ({group_x + group_w}) should be >= "
                f"max(x+w) + 20 ({max_right + 20}), positions={positions}"
            )
            # Top padding (group_y should accommodate label area too)
            self.assertLessEqual(
                group_y, min_y - 20,
                f"Trial {trial}: group_y ({group_y}) should be <= "
                f"min(y) - 20 ({min_y - 20}), positions={positions}"
            )
            # Bottom padding
            self.assertGreaterEqual(
                group_y + group_h, max_bottom + 20,
                f"Trial {trial}: group_y+group_h ({group_y + group_h}) should be >= "
                f"max(y+h) + 20 ({max_bottom + 20}), positions={positions}"
            )


if __name__ == "__main__":
    unittest.main()
