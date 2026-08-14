"""Property test: Loop Enclosure (Property 8).

For any first_node_y, last_node_y, last_node_h, and sw_w, verify the annotation
rectangle fully contains the node range with >= 15px padding on all sides.

Validates: Requirements 5.3, 5.4
"""

import random
import subprocess
import sys
import unittest

LAYOUT_PY = "claude/skills/diagram/layout.py"
NUM_TRIALS = 100


def run_loop_annotation(first_node_y, last_node_y, last_node_h, sw_w):
    """Run the loop-annotation command and parse its output."""
    result = subprocess.run(
        [sys.executable, LAYOUT_PY, "loop-annotation",
         str(first_node_y), str(last_node_y), str(last_node_h), str(sw_w)],
        capture_output=True, text=True,
        cwd="/Users/aadam.haq/Code/drawio-skill",
    )
    if result.returncode != 0:
        raise RuntimeError(f"loop-annotation failed: {result.stderr}")

    parsed = {}
    for line in result.stdout.strip().splitlines():
        # Each line looks like: annotation_x=4
        for part in line.split():
            if "=" in part:
                key, val = part.split("=", 1)
                parsed[key] = int(val)
    return parsed


class TestLoopEnclosureProperty(unittest.TestCase):
    """Property 8: Loop Enclosure.

    For any first_node_y (1-500), last_node_y (>= first_node_y, up to
    first_node_y + 500), last_node_h (36-100), and sw_w (100-500), verify:
    1. annotation_y <= first_node_y - 15 (top padding >= 15px above first node)
    2. annotation_y + annotation_h >= last_node_y + last_node_h + 15 (bottom padding >= 15px below last node)
    3. annotation_w == sw_w - 8 (4px margin each side)
    4. annotation_x == 4 (always)
    5. annotation_h > 0
    6. label_x is within the annotation box
    7. label_y is within the annotation box

    Validates: Requirements 5.3, 5.4
    """

    def test_loop_enclosure_property(self):
        """Run 100 randomized trials verifying loop enclosure invariants."""
        rng = random.Random(42)  # Deterministic seed for reproducibility

        for trial in range(NUM_TRIALS):
            first_node_y = rng.randint(1, 500)
            last_node_y = rng.randint(first_node_y, first_node_y + 500)
            last_node_h = rng.randint(36, 100)
            sw_w = rng.randint(100, 500)

            with self.subTest(trial=trial, first_node_y=first_node_y,
                              last_node_y=last_node_y, last_node_h=last_node_h,
                              sw_w=sw_w):
                out = run_loop_annotation(first_node_y, last_node_y, last_node_h, sw_w)

                annotation_x = out["annotation_x"]
                annotation_y = out["annotation_y"]
                annotation_w = out["annotation_w"]
                annotation_h = out["annotation_h"]
                label_x = out["label_x"]
                label_y = out["label_y"]

                # 1. Top padding: annotation_y <= first_node_y - 15
                self.assertLessEqual(
                    annotation_y, first_node_y - 15,
                    f"Top padding violated: annotation_y={annotation_y} > "
                    f"first_node_y - 15 = {first_node_y - 15}"
                )

                # 2. Bottom padding: annotation_y + annotation_h >= last_node_y + last_node_h + 15
                annotation_bottom = annotation_y + annotation_h
                required_bottom = last_node_y + last_node_h + 15
                self.assertGreaterEqual(
                    annotation_bottom, required_bottom,
                    f"Bottom padding violated: annotation_bottom={annotation_bottom} < "
                    f"last_node_y + last_node_h + 15 = {required_bottom}"
                )

                # 3. Width: annotation_w == sw_w - 8
                self.assertEqual(
                    annotation_w, sw_w - 8,
                    f"Width violated: annotation_w={annotation_w} != sw_w - 8 = {sw_w - 8}"
                )

                # 4. annotation_x == 4
                self.assertEqual(
                    annotation_x, 4,
                    f"annotation_x={annotation_x} != 4"
                )

                # 5. annotation_h > 0
                self.assertGreater(
                    annotation_h, 0,
                    f"annotation_h={annotation_h} is not positive"
                )

                # 6. label_x within annotation box
                self.assertGreaterEqual(
                    label_x, annotation_x,
                    f"label_x={label_x} < annotation_x={annotation_x}"
                )
                self.assertLessEqual(
                    label_x, annotation_x + annotation_w,
                    f"label_x={label_x} > annotation_x + annotation_w="
                    f"{annotation_x + annotation_w}"
                )

                # 7. label_y within annotation box
                self.assertGreaterEqual(
                    label_y, annotation_y,
                    f"label_y={label_y} < annotation_y={annotation_y}"
                )
                self.assertLessEqual(
                    label_y, annotation_y + annotation_h,
                    f"label_y={label_y} > annotation_y + annotation_h="
                    f"{annotation_y + annotation_h}"
                )


if __name__ == "__main__":
    unittest.main()
