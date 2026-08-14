#!/usr/bin/env python3
"""Property-based test: Nested Container Containment

**Validates: Requirements 5.1, 5.2**

Property 10: For any parent_sw_w >= 100 and any number of children (1-10)
with any line counts (1-5 per child), verify:
1. child_step_w == parent_sw_w - 60 (always)
2. container_w == parent_sw_w - 24 (always)
3. All child y-positions are >= 20 (header area)
4. container_h > 0
5. All children fit within container_h (last child y + h <= container_h - 20)
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


def run_nested_container(parent_sw_w, parent_start_y, n_children, lines_per_child):
    """Run layout.py nested-container and return parsed output as a dict."""
    args = [
        sys.executable, LAYOUT_PY,
        "nested-container",
        str(parent_sw_w),
        str(parent_start_y),
        str(n_children),
    ] + [str(l) for l in lines_per_child]

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"nested-container failed (exit {result.returncode}): {result.stderr}"
        )

    output = result.stdout.strip()
    parsed = {}

    # Parse container_x, container_y, container_w from first line
    m = re.search(r"container_x=(\d+)", output)
    if m:
        parsed["container_x"] = int(m.group(1))
    m = re.search(r"container_y=(\d+)", output)
    if m:
        parsed["container_y"] = int(m.group(1))
    m = re.search(r"container_w=(\d+)", output)
    if m:
        parsed["container_w"] = int(m.group(1))

    # Parse child_step_w, child_step_x
    m = re.search(r"child_step_w=(\d+)", output)
    if m:
        parsed["child_step_w"] = int(m.group(1))
    m = re.search(r"child_step_x=(\d+)", output)
    if m:
        parsed["child_step_x"] = int(m.group(1))

    # Parse each child's y and h
    children = []
    for match in re.finditer(r"child\[(\d+)\]: y=(\d+)\s+h=(\d+)", output):
        children.append({"index": int(match.group(1)), "y": int(match.group(2)), "h": int(match.group(3))})
    parsed["children"] = children

    # Parse container_h
    m = re.search(r"container_h=(\d+)", output)
    if m:
        parsed["container_h"] = int(m.group(1))

    return parsed


class TestNestedContainerContainment(unittest.TestCase):
    """Property 10: Nested Container Containment

    For any valid inputs, verify structural invariants hold.
    """

    NUM_TRIALS = 100
    SEED = 42

    def setUp(self):
        self.rng = random.Random(self.SEED)

    def _generate_input(self):
        """Generate a random valid input for nested-container."""
        parent_sw_w = self.rng.randint(100, 500)
        parent_start_y = self.rng.randint(0, 200)
        n_children = self.rng.randint(1, 8)
        lines_per_child = [self.rng.randint(1, 5) for _ in range(n_children)]
        return parent_sw_w, parent_start_y, n_children, lines_per_child

    def test_property_child_step_w_equals_parent_minus_60(self):
        """Property 10.1: child_step_w == parent_sw_w - 60 for all valid inputs."""
        for _ in range(self.NUM_TRIALS):
            parent_sw_w, parent_start_y, n_children, lines = self._generate_input()
            result = run_nested_container(parent_sw_w, parent_start_y, n_children, lines)
            self.assertEqual(
                result["child_step_w"], parent_sw_w - 60,
                f"child_step_w should be parent_sw_w-60 for parent_sw_w={parent_sw_w}"
            )

    def test_property_container_w_equals_parent_minus_24(self):
        """Property 10.2: container_w == parent_sw_w - 24 for all valid inputs."""
        for _ in range(self.NUM_TRIALS):
            parent_sw_w, parent_start_y, n_children, lines = self._generate_input()
            result = run_nested_container(parent_sw_w, parent_start_y, n_children, lines)
            self.assertEqual(
                result["container_w"], parent_sw_w - 24,
                f"container_w should be parent_sw_w-24 for parent_sw_w={parent_sw_w}"
            )

    def test_property_all_children_below_header(self):
        """Property 10.3: All child y-positions are >= 20 (header area)."""
        for _ in range(self.NUM_TRIALS):
            parent_sw_w, parent_start_y, n_children, lines = self._generate_input()
            result = run_nested_container(parent_sw_w, parent_start_y, n_children, lines)
            for child in result["children"]:
                self.assertGreaterEqual(
                    child["y"], 20,
                    f"child[{child['index']}] y={child['y']} should be >= 20 "
                    f"(header area) for inputs: parent_sw_w={parent_sw_w}, "
                    f"n_children={n_children}, lines={lines}"
                )

    def test_property_container_h_positive(self):
        """Property 10.4: container_h > 0 for all valid inputs."""
        for _ in range(self.NUM_TRIALS):
            parent_sw_w, parent_start_y, n_children, lines = self._generate_input()
            result = run_nested_container(parent_sw_w, parent_start_y, n_children, lines)
            self.assertGreater(
                result["container_h"], 0,
                f"container_h should be > 0 for inputs: parent_sw_w={parent_sw_w}, "
                f"n_children={n_children}, lines={lines}"
            )

    def test_property_children_fit_within_container(self):
        """Property 10.5: All children fit within container_h (last child y + h <= container_h - 20)."""
        for _ in range(self.NUM_TRIALS):
            parent_sw_w, parent_start_y, n_children, lines = self._generate_input()
            result = run_nested_container(parent_sw_w, parent_start_y, n_children, lines)
            children = result["children"]
            container_h = result["container_h"]
            if children:
                last_child = children[-1]
                last_child_bottom = last_child["y"] + last_child["h"]
                self.assertLessEqual(
                    last_child_bottom, container_h - 20,
                    f"Last child bottom ({last_child_bottom}) should be <= "
                    f"container_h - 20 ({container_h - 20}) for inputs: "
                    f"parent_sw_w={parent_sw_w}, n_children={n_children}, lines={lines}"
                )


if __name__ == "__main__":
    unittest.main()
