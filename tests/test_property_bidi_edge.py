"""Property test: Bidirectional Edge Separation (Property 7).

For random non-overlapping source/target box positions, verify:
1. Forward and reverse edges use different exitY/entryY values (horizontal) or
   different exitX/entryX values (vertical)
2. The separation between forward and reverse paths equals 2*offset/box_dimension
3. Exit/entry values are all in [0.0, 1.0] range
4. For horizontal dominant: both edges exit from the same X side (0 or 1) but different Y offsets
5. For vertical dominant: both edges exit from the same Y side (0 or 1) but different X offsets

Validates: Requirements 4.1, 4.2, 4.3
"""

import random
import subprocess
import sys
import unittest

LAYOUT_PY = "claude/skills/diagram/layout.py"
NUM_TRIALS = 80


def run_bidirectional_edge(src_x, src_y, src_w, src_h, tgt_x, tgt_y, tgt_w, tgt_h, offset):
    """Run the bidirectional-edge command and parse its output."""
    result = subprocess.run(
        [sys.executable, LAYOUT_PY, "bidirectional-edge",
         str(src_x), str(src_y), str(src_w), str(src_h),
         str(tgt_x), str(tgt_y), str(tgt_w), str(tgt_h),
         str(offset)],
        capture_output=True, text=True,
        cwd="/Users/aadam.haq/Code/drawio-skill",
    )
    if result.returncode != 0:
        raise RuntimeError(f"bidirectional-edge failed: {result.stderr}")

    parsed = {}
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith("forward:"):
            prefix = "fwd_"
            parts = line[len("forward:"):].strip().split()
        elif line.startswith("reverse:"):
            prefix = "rev_"
            parts = line[len("reverse:"):].strip().split()
        else:
            continue
        for part in parts:
            if "=" in part:
                key, val = part.split("=", 1)
                parsed[prefix + key] = float(val)
    return parsed


def generate_non_overlapping_boxes(rng):
    """Generate two non-overlapping boxes placed far enough apart."""
    src_w = rng.randint(60, 200)
    src_h = rng.randint(40, 150)
    tgt_w = rng.randint(60, 200)
    tgt_h = rng.randint(40, 150)

    src_x = rng.randint(0, 400)
    src_y = rng.randint(0, 400)

    # Place target far enough away to guarantee no overlap
    direction = rng.choice(["right", "left", "below", "above"])
    gap = rng.randint(50, 300)

    if direction == "right":
        tgt_x = src_x + src_w + gap
        tgt_y = src_y + rng.randint(-100, 100)
    elif direction == "left":
        tgt_x = src_x - tgt_w - gap
        tgt_y = src_y + rng.randint(-100, 100)
    elif direction == "below":
        tgt_x = src_x + rng.randint(-100, 100)
        tgt_y = src_y + src_h + gap
    else:  # above
        tgt_x = src_x + rng.randint(-100, 100)
        tgt_y = src_y - tgt_h - gap

    return src_x, src_y, src_w, src_h, tgt_x, tgt_y, tgt_w, tgt_h


class TestBidirectionalEdgeSeparation(unittest.TestCase):
    """Property 7: Bidirectional Edge Separation.

    For 80 random non-overlapping source/target box configurations, verify:
    1. Forward and reverse edges use different exitY/entryY (horizontal) or exitX/entryX (vertical)
    2. Separation equals 2*offset/box_dimension
    3. All exit/entry values in [0.0, 1.0]
    4. Horizontal dominant: same X side, different Y offsets
    5. Vertical dominant: same Y side, different X offsets

    Validates: Requirements 4.1, 4.2, 4.3
    """

    def test_bidirectional_edge_separation_property(self):
        """Run 80 randomized trials verifying bidirectional edge invariants."""
        rng = random.Random(42)

        for trial in range(NUM_TRIALS):
            src_x, src_y, src_w, src_h, tgt_x, tgt_y, tgt_w, tgt_h = \
                generate_non_overlapping_boxes(rng)
            offset = rng.randint(4, 16)

            with self.subTest(trial=trial, src_x=src_x, src_y=src_y,
                              src_w=src_w, src_h=src_h, tgt_x=tgt_x,
                              tgt_y=tgt_y, tgt_w=tgt_w, tgt_h=tgt_h,
                              offset=offset):
                out = run_bidirectional_edge(
                    src_x, src_y, src_w, src_h,
                    tgt_x, tgt_y, tgt_w, tgt_h, offset
                )

                fwd_exitX = out["fwd_exitX"]
                fwd_exitY = out["fwd_exitY"]
                fwd_entryX = out["fwd_entryX"]
                fwd_entryY = out["fwd_entryY"]
                rev_exitX = out["rev_exitX"]
                rev_exitY = out["rev_exitY"]
                rev_entryX = out["rev_entryX"]
                rev_entryY = out["rev_entryY"]

                # Determine dominant direction
                src_cx = src_x + src_w / 2.0
                src_cy = src_y + src_h / 2.0
                tgt_cx = tgt_x + tgt_w / 2.0
                tgt_cy = tgt_y + tgt_h / 2.0
                dx = tgt_cx - src_cx
                dy = tgt_cy - src_cy
                horizontal_dominant = abs(dx) > abs(dy)

                # --- Invariant 3: All exit/entry values in [0.0, 1.0] ---
                for name, val in [("fwd_exitX", fwd_exitX), ("fwd_exitY", fwd_exitY),
                                  ("fwd_entryX", fwd_entryX), ("fwd_entryY", fwd_entryY),
                                  ("rev_exitX", rev_exitX), ("rev_exitY", rev_exitY),
                                  ("rev_entryX", rev_entryX), ("rev_entryY", rev_entryY)]:
                    self.assertGreaterEqual(
                        val, 0.0,
                        f"{name}={val} is below 0.0"
                    )
                    self.assertLessEqual(
                        val, 1.0,
                        f"{name}={val} is above 1.0"
                    )

                if horizontal_dominant:
                    # --- Invariant 1: Different exitY/entryY ---
                    self.assertNotAlmostEqual(
                        fwd_exitY, rev_entryY, places=6,
                        msg=f"Forward exitY={fwd_exitY} should differ from "
                            f"reverse entryY={rev_entryY} (horizontal)"
                    )
                    self.assertNotAlmostEqual(
                        fwd_entryY, rev_exitY, places=6,
                        msg=f"Forward entryY={fwd_entryY} should differ from "
                            f"reverse exitY={rev_exitY} (horizontal)"
                    )

                    # --- Invariant 2: Separation = 2*offset/box_dimension ---
                    # Source side: fwd exits at 0.5 - offset/src_h, rev enters at 0.5 + offset/src_h
                    # Note: layout.py uses :.4g formatting, so we use places=3 tolerance
                    expected_src_sep = 2 * offset / src_h
                    actual_src_sep = abs(rev_entryY - fwd_exitY)
                    self.assertAlmostEqual(
                        actual_src_sep, expected_src_sep, places=3,
                        msg=f"Source separation: actual={actual_src_sep:.6f} "
                            f"expected={expected_src_sep:.6f}"
                    )
                    # Target side: fwd enters at 0.5 - offset/tgt_h, rev exits at 0.5 + offset/tgt_h
                    expected_tgt_sep = 2 * offset / tgt_h
                    actual_tgt_sep = abs(rev_exitY - fwd_entryY)
                    self.assertAlmostEqual(
                        actual_tgt_sep, expected_tgt_sep, places=3,
                        msg=f"Target separation: actual={actual_tgt_sep:.6f} "
                            f"expected={expected_tgt_sep:.6f}"
                    )

                    # --- Invariant 4: Same X side, different Y offsets ---
                    self.assertEqual(
                        fwd_exitX, rev_entryX,
                        f"Horizontal: fwd_exitX={fwd_exitX} should equal "
                        f"rev_entryX={rev_entryX} (same side)"
                    )
                    self.assertEqual(
                        fwd_entryX, rev_exitX,
                        f"Horizontal: fwd_entryX={fwd_entryX} should equal "
                        f"rev_exitX={rev_exitX} (same side)"
                    )
                    # Verify X sides are 0 or 1
                    self.assertIn(fwd_exitX, (0.0, 1.0),
                                  f"fwd_exitX={fwd_exitX} should be 0 or 1")
                    self.assertIn(fwd_entryX, (0.0, 1.0),
                                  f"fwd_entryX={fwd_entryX} should be 0 or 1")

                else:
                    # --- Invariant 1: Different exitX/entryX ---
                    self.assertNotAlmostEqual(
                        fwd_exitX, rev_entryX, places=6,
                        msg=f"Forward exitX={fwd_exitX} should differ from "
                            f"reverse entryX={rev_entryX} (vertical)"
                    )
                    self.assertNotAlmostEqual(
                        fwd_entryX, rev_exitX, places=6,
                        msg=f"Forward entryX={fwd_entryX} should differ from "
                            f"reverse exitX={rev_exitX} (vertical)"
                    )

                    # --- Invariant 2: Separation = 2*offset/box_dimension ---
                    # Source side: fwd exits at 0.5 + offset/src_w, rev enters at 0.5 - offset/src_w
                    # Note: layout.py uses :.4g formatting, so we use places=3 tolerance
                    expected_src_sep = 2 * offset / src_w
                    actual_src_sep = abs(fwd_exitX - rev_entryX)
                    self.assertAlmostEqual(
                        actual_src_sep, expected_src_sep, places=3,
                        msg=f"Source separation: actual={actual_src_sep:.6f} "
                            f"expected={expected_src_sep:.6f}"
                    )
                    # Target side: fwd enters at 0.5 + offset/tgt_w, rev exits at 0.5 - offset/tgt_w
                    expected_tgt_sep = 2 * offset / tgt_w
                    actual_tgt_sep = abs(fwd_entryX - rev_exitX)
                    self.assertAlmostEqual(
                        actual_tgt_sep, expected_tgt_sep, places=3,
                        msg=f"Target separation: actual={actual_tgt_sep:.6f} "
                            f"expected={expected_tgt_sep:.6f}"
                    )

                    # --- Invariant 5: Same Y side, different X offsets ---
                    self.assertEqual(
                        fwd_exitY, rev_entryY,
                        f"Vertical: fwd_exitY={fwd_exitY} should equal "
                        f"rev_entryY={rev_entryY} (same side)"
                    )
                    self.assertEqual(
                        fwd_entryY, rev_exitY,
                        f"Vertical: fwd_entryY={fwd_entryY} should equal "
                        f"rev_exitY={rev_exitY} (same side)"
                    )
                    # Verify Y sides are 0 or 1
                    self.assertIn(fwd_exitY, (0.0, 1.0),
                                  f"fwd_exitY={fwd_exitY} should be 0 or 1")
                    self.assertIn(fwd_entryY, (0.0, 1.0),
                                  f"fwd_entryY={fwd_entryY} should be 0 or 1")


if __name__ == "__main__":
    unittest.main()
