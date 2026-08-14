"""Property test: No-Overlap and Page Containment (Property 6).

For N in [1, 15], with random layer assignments, verify:
1. All bounding boxes are non-overlapping (for any two services i, j with i≠j)
2. All positions are within page bounds: x >= 0, y >= 0, x+w <= 1169, y+h <= 827
3. Services in the same layer have the same y coordinate
4. Services in different layers have different y coordinates (monotonic by layer order)

Validates: Requirements 7.1, 7.2
"""

import random
import subprocess
import sys
import unittest

LAYOUT_PY = "claude/skills/diagram/layout.py"
NUM_TRIALS = 80
VALID_LAYERS = ["client", "gateway", "service", "worker", "infrastructure"]
PAGE_W = 1169
PAGE_H = 827


def run_service_map(n_services, layer_hints):
    """Run the service-map command and parse its output."""
    cmd = [sys.executable, LAYOUT_PY, "service-map", str(n_services)] + layer_hints
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
        cwd="/Users/aadam.haq/Code/drawio-skill",
    )
    if result.returncode != 0:
        raise RuntimeError(f"service-map failed: {result.stderr}")

    services = []
    for line in result.stdout.strip().splitlines():
        if line.startswith("service["):
            # Parse: service[0]: x=494 y=60 w=180 h=120 layer=client
            parts = line.split(":", 1)[1].strip().split()
            entry = {}
            for part in parts:
                if "=" in part:
                    key, val = part.split("=", 1)
                    if key in ("x", "y", "w", "h"):
                        entry[key] = int(val)
                    elif key == "layer":
                        entry[key] = val
            services.append(entry)
    return services


def boxes_overlap(a, b):
    """Return True if two bounding boxes (dicts with x, y, w, h) overlap."""
    # No overlap if one is entirely to the left, right, above, or below the other
    if a["x"] + a["w"] <= b["x"]:
        return False
    if b["x"] + b["w"] <= a["x"]:
        return False
    if a["y"] + a["h"] <= b["y"]:
        return False
    if b["y"] + b["h"] <= a["y"]:
        return False
    return True


class TestServiceMapNoOverlapProperty(unittest.TestCase):
    """Property 6: No-Overlap and Page Containment.

    For random n_services (1-15) and random layer hints, verify:
    1. No two service bounding boxes overlap
    2. All services are within page bounds (0,0)-(1169,827)
    3. Services in the same layer share the same y coordinate
    4. Services in different layers have different y coordinates (monotonic by layer order)

    Validates: Requirements 7.1, 7.2
    """

    def test_no_overlap_and_page_containment(self):
        """Run 80 randomized trials verifying service-map invariants."""
        rng = random.Random(42)  # Deterministic seed for reproducibility

        for trial in range(NUM_TRIALS):
            n_services = rng.randint(1, 15)
            layer_hints = [rng.choice(VALID_LAYERS) for _ in range(n_services)]

            with self.subTest(trial=trial, n_services=n_services,
                              layer_hints=layer_hints):
                services = run_service_map(n_services, layer_hints)

                self.assertEqual(
                    len(services), n_services,
                    f"Expected {n_services} services, got {len(services)}"
                )

                # Invariant 1: No two bounding boxes overlap
                for i in range(len(services)):
                    for j in range(i + 1, len(services)):
                        self.assertFalse(
                            boxes_overlap(services[i], services[j]),
                            f"Services {i} and {j} overlap: "
                            f"{services[i]} vs {services[j]}"
                        )

                # Invariant 2: All positions within page bounds
                for i, svc in enumerate(services):
                    self.assertGreaterEqual(
                        svc["x"], 0,
                        f"Service {i} x={svc['x']} is negative"
                    )
                    self.assertGreaterEqual(
                        svc["y"], 0,
                        f"Service {i} y={svc['y']} is negative"
                    )
                    self.assertLessEqual(
                        svc["x"] + svc["w"], PAGE_W,
                        f"Service {i} right edge {svc['x'] + svc['w']} "
                        f"exceeds page width {PAGE_W}"
                    )
                    self.assertLessEqual(
                        svc["y"] + svc["h"], PAGE_H,
                        f"Service {i} bottom edge {svc['y'] + svc['h']} "
                        f"exceeds page height {PAGE_H}"
                    )

                # Invariant 3: Services in the same layer have the same y
                layer_to_y = {}
                for i, svc in enumerate(services):
                    layer = svc["layer"]
                    if layer in layer_to_y:
                        self.assertEqual(
                            svc["y"], layer_to_y[layer],
                            f"Service {i} (layer={layer}) has y={svc['y']} "
                            f"but expected y={layer_to_y[layer]} "
                            f"(same layer, should match)"
                        )
                    else:
                        layer_to_y[layer] = svc["y"]

                # Invariant 4: Services in different layers have different y
                # coordinates that are monotonically increasing by layer order
                layer_order = [l for l in VALID_LAYERS if l in layer_to_y]
                for idx in range(len(layer_order) - 1):
                    y_curr = layer_to_y[layer_order[idx]]
                    y_next = layer_to_y[layer_order[idx + 1]]
                    self.assertLess(
                        y_curr, y_next,
                        f"Layer '{layer_order[idx]}' y={y_curr} is not less "
                        f"than layer '{layer_order[idx + 1]}' y={y_next} "
                        f"(should be monotonically increasing)"
                    )


if __name__ == "__main__":
    unittest.main()
