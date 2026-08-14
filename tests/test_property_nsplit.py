"""Property test: N-Split Box Coverage (Property 11).

Validates: Requirements 5.5

For any N >= 2 (up to 10) and any sw_w >= 100, verify:
1. All N outcome boxes are non-overlapping (x[i] + w[i] <= x[i+1] for adjacent boxes)
2. All boxes have width > 0
3. The first box starts at x=18
4. The last box ends at or before 18 + step_w (where step_w = sw_w - 36)
5. split_y is correctly computed as last_step_y + last_step_h + split_gap
6. sl_height == split_y + 36 + 20
"""

import math
import random
import re
import subprocess
import sys
import unittest

LAYOUT_PY = "claude/skills/diagram/layout.py"
NUM_SAMPLES = 80


def run_n_split(sw_w, last_step_y, last_step_h, n_outcomes, split_gap):
    """Run layout.py n-split and return parsed output."""
    cmd = [
        sys.executable, LAYOUT_PY,
        "n-split",
        str(sw_w), str(last_step_y), str(last_step_h),
        str(n_outcomes), str(split_gap),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(
            f"n-split failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def parse_output(output, n_outcomes):
    """Parse n-split output into structured data."""
    lines = output.splitlines()
    data = {}

    # Parse split_y
    for line in lines:
        m = re.match(r"split_y=(\d+)", line)
        if m:
            data["split_y"] = int(m.group(1))
            break

    # Parse outcome boxes
    outcomes = []
    for line in lines:
        m = re.match(r"outcome\[(\d+)\]:\s*x=(\d+)\s+w=(\d+)", line)
        if m:
            outcomes.append({"index": int(m.group(1)), "x": int(m.group(2)), "w": int(m.group(3))})

    data["outcomes"] = sorted(outcomes, key=lambda o: o["index"])

    # Parse sl_height
    for line in lines:
        m = re.match(r"sl_height=(\d+)", line)
        if m:
            data["sl_height"] = int(m.group(1))
            break

    return data


class TestNSplitBoxCoverage(unittest.TestCase):
    """Property 11: N-Split Box Coverage.

    **Validates: Requirements 5.5**
    """

    def setUp(self):
        """Generate random valid inputs for property testing."""
        random.seed(42)
        self.samples = []
        for _ in range(NUM_SAMPLES):
            sw_w = random.randint(100, 500)
            n_outcomes = random.randint(2, 10)
            last_step_y = random.randint(45, 500)
            last_step_h = random.randint(36, 100)
            split_gap = random.randint(20, 80)
            self.samples.append({
                "sw_w": sw_w,
                "n_outcomes": n_outcomes,
                "last_step_y": last_step_y,
                "last_step_h": last_step_h,
                "split_gap": split_gap,
            })

    def test_boxes_non_overlapping(self):
        """All N outcome boxes are non-overlapping: x[i] + w[i] <= x[i+1]."""
        for sample in self.samples:
            with self.subTest(**sample):
                output = run_n_split(
                    sample["sw_w"], sample["last_step_y"],
                    sample["last_step_h"], sample["n_outcomes"],
                    sample["split_gap"],
                )
                data = parse_output(output, sample["n_outcomes"])
                outcomes = data["outcomes"]
                self.assertEqual(len(outcomes), sample["n_outcomes"])

                for i in range(len(outcomes) - 1):
                    right_edge = outcomes[i]["x"] + outcomes[i]["w"]
                    next_x = outcomes[i + 1]["x"]
                    self.assertLessEqual(
                        right_edge, next_x,
                        f"Box {i} overlaps box {i+1}: "
                        f"x={outcomes[i]['x']} w={outcomes[i]['w']} "
                        f"right_edge={right_edge} > next_x={next_x} "
                        f"(sw_w={sample['sw_w']}, n={sample['n_outcomes']})"
                    )

    def test_boxes_positive_width(self):
        """All boxes have width > 0."""
        for sample in self.samples:
            with self.subTest(**sample):
                output = run_n_split(
                    sample["sw_w"], sample["last_step_y"],
                    sample["last_step_h"], sample["n_outcomes"],
                    sample["split_gap"],
                )
                data = parse_output(output, sample["n_outcomes"])
                for outcome in data["outcomes"]:
                    self.assertGreater(
                        outcome["w"], 0,
                        f"Box {outcome['index']} has non-positive width: "
                        f"w={outcome['w']} "
                        f"(sw_w={sample['sw_w']}, n={sample['n_outcomes']})"
                    )

    def test_first_box_starts_at_18(self):
        """The first box starts at x=18."""
        for sample in self.samples:
            with self.subTest(**sample):
                output = run_n_split(
                    sample["sw_w"], sample["last_step_y"],
                    sample["last_step_h"], sample["n_outcomes"],
                    sample["split_gap"],
                )
                data = parse_output(output, sample["n_outcomes"])
                outcomes = data["outcomes"]
                self.assertEqual(
                    outcomes[0]["x"], 18,
                    f"First box x={outcomes[0]['x']} != 18 "
                    f"(sw_w={sample['sw_w']}, n={sample['n_outcomes']})"
                )

    def test_last_box_within_step_w(self):
        """The last box ends at or before 18 + step_w."""
        for sample in self.samples:
            with self.subTest(**sample):
                step_w = sample["sw_w"] - 36
                output = run_n_split(
                    sample["sw_w"], sample["last_step_y"],
                    sample["last_step_h"], sample["n_outcomes"],
                    sample["split_gap"],
                )
                data = parse_output(output, sample["n_outcomes"])
                outcomes = data["outcomes"]
                last = outcomes[-1]
                right_edge = last["x"] + last["w"]
                max_right = 18 + step_w
                self.assertLessEqual(
                    right_edge, max_right,
                    f"Last box right_edge={right_edge} > 18+step_w={max_right} "
                    f"(sw_w={sample['sw_w']}, step_w={step_w}, n={sample['n_outcomes']})"
                )

    def test_split_y_computation(self):
        """split_y == last_step_y + last_step_h + split_gap."""
        for sample in self.samples:
            with self.subTest(**sample):
                expected_split_y = (
                    sample["last_step_y"] + sample["last_step_h"] + sample["split_gap"]
                )
                output = run_n_split(
                    sample["sw_w"], sample["last_step_y"],
                    sample["last_step_h"], sample["n_outcomes"],
                    sample["split_gap"],
                )
                data = parse_output(output, sample["n_outcomes"])
                self.assertEqual(
                    data["split_y"], expected_split_y,
                    f"split_y={data['split_y']} != expected {expected_split_y} "
                    f"(last_step_y={sample['last_step_y']}, "
                    f"last_step_h={sample['last_step_h']}, "
                    f"split_gap={sample['split_gap']})"
                )

    def test_sl_height_computation(self):
        """sl_height == split_y + 36 + 20."""
        for sample in self.samples:
            with self.subTest(**sample):
                output = run_n_split(
                    sample["sw_w"], sample["last_step_y"],
                    sample["last_step_h"], sample["n_outcomes"],
                    sample["split_gap"],
                )
                data = parse_output(output, sample["n_outcomes"])
                expected_sl_height = data["split_y"] + 36 + 20
                self.assertEqual(
                    data["sl_height"], expected_sl_height,
                    f"sl_height={data['sl_height']} != split_y+56={expected_sl_height} "
                    f"(split_y={data['split_y']})"
                )


if __name__ == "__main__":
    unittest.main()
