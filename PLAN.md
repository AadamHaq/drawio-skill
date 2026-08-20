# Improvement Plan — Round 4 (Final Polish)

## Findings from v5

- **auto-eval**: No complaints (PIPELINE vertical layout works well)
- **convai p1**: Legend text at y=1084-1126 — viewBox goes to y=1160 so it should be visible. The "header overflows from the bottom" likely means the swimlane header rect at the bottom of the page is partially cut off. Need to check if the legend/footer content is being clipped.
- **convai-lab**: Multiple issues:
  - **Box overlap**: frozenarms (x=520, w=240) overlaps convai-note (x=700, w=220) by 60px
  - **Items touch band bottom**: ALL items have 0px clearance from their band's bottom edge. Items at y=84,h=70 → bottom=154, band bottom=154. Looks like items are jammed against the band border with no breathing room.
  - **Arrows cross headers**: edges from L1 items (bottom at y=328) to L2 items (y=432) cross through L2's header zone (y=378-406). Waypoints are at y=345 (in the gap) which is good, but then the edge goes straight to y=432 crossing through the L2 header (378-406).
  - **Labels overlapping**: with 0px clearance at band bottom, labels on edges between bands sit in the 50px gap but overlap visually with the band border and header of the next band.

## Root Causes

1. **Band height too tight** — `h=124` for a band containing startSize=28 + 26 clearance + 70 item height = 124. That leaves ZERO bottom padding. Items touch the band border exactly. Need: 28 + 26 + 70 + **20 bottom pad** = 144 minimum.

2. **Box overlap** — Two items (frozenarms + convai-note) positioned at same y with overlapping x ranges. The agent didn't check horizontal collision.

3. **Header crossing on entry** — Edge from L1→L2 has waypoint at y=345 (good, in gap) but then goes straight from y=345 to y=432. The segment from 345→432 crosses through L2's header (378-406). The waypoint rule says "waypoint in the GAP" but the gap ends at the NEXT band's top (378), and the edge continues straight through the header to the item at 432. Need another waypoint BELOW the header.

4. **Convai legend clipping** — The viewBox calculation might not include all text at the very bottom if the text starts inside the box but extends below.

## Plan

### Fix 1: Band bottom padding (15px minimum)

- File: `layered/render.md`
- Rule: "Band height = startSize + 26 (clearance) + item_height + **20** (bottom padding). Never less."
- Update `layout.py layers`: compute layer_h = startSize + 26 + max_item_h + 20
- This gives 10px between item bottom and band border, preventing the "touching" look.

### Fix 2: Horizontal collision detection in validate.py

- New check: if two root-level sibling items (same y-range) overlap on the x-axis, flag it.
- Already partially done (found the frozenarms/convai-note overlap) — just need it in validate.py.

### Fix 3: Edge must have waypoint BELOW target band header (not just in the gap)

- File: `layered/render.md`
- Update the waypoint rule: "Cross-band edges need TWO waypoints: one in the gap between bands, AND one at target_band_y + startSize + 5 (below the header) if the target item is further inside."
- OR simpler: "The edge should enter the item directly (not the band). If the item is a root-level sibling, the entry point is the item's own y=0, which is below the header. The edge just needs a waypoint in the gap — the Z-route from gap to item y will clear the header."
- The real issue: the current waypoint at y=345 is in the L1→L2 gap, but the edge then goes straight to y=432 crossing L2's header (378-406). The fix: add a second waypoint at y=410 (just below L2 header at 406).

### Fix 4: ViewBox includes bottom text

- File: `render_svg.py`
- The text bound scan already includes text y-positions but doesn't account for text HEIGHT (each line is ~14px below the y value). Add text_h (14px) to the max_y calculation for text elements.

### Fix 5: Update layout.py layers to output band heights with padding

- Currently bands are 80px base height. With startSize=28 + 26 clearance + 40 item height (minimum), that's only 94px. For items that are 70px tall: 28+26+70+20=144.
- The `layers` command should compute: `layer_h = startSize + 26 + item_h + 20`
- Where item_h is computed from the number of lines (currently `layer_h - 30 - 10`).

## Priority

1. Fix 1 + Fix 5 (band padding) — prevents all the "touching bottom" issues
2. Fix 3 (double waypoint) — prevents header crossing on band entry
3. Fix 2 (horizontal overlap) — catches collision before user sees it
4. Fix 4 (text height in viewBox) — prevents bottom clipping
