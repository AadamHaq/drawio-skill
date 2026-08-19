# Pre-Write Validation Checklist

Run through EVERY item below before writing the .drawio file. If ANY check fails, fix it first.

## Edge Checks (do for EVERY edge in the diagram)

1. **Does this edge have `edgeStyle=orthogonalEdgeStyle;rounded=1;`?**
   - YES → good, draw.io will auto-route around boxes
   - NO → add it

2. **Does this edge use waypoints from the edge planner?**
   - Cross-service/cross-row edges: SHOULD have waypoints computed by `edge_planner.py`
   - Sequential edges within a swimlane: should NOT have waypoints (straight down)
   - If a cross-service edge has no waypoints and goes far, it may route through boxes

3. **Does this edge have a short label (value attribute)?**
   - Cross-service/cross-row edges: MUST have a label (5-15 chars)
   - Sequential edges within a swimlane: empty label is fine
   - If a label would be longer than 15 chars, abbreviate it

4. **Are the exit/entry points spread out?**
   - If 3+ edges leave the same node, they must use different exitX values (e.g., 0.2, 0.5, 0.8 — NOT 0.4, 0.5, 0.6)
   - If 3+ edges enter the same node, they must use different entryX values with at least 0.15 spacing

5. **Is the strokeWidth at least 2?** (3 for gRPC)
   - Thin lines are invisible

## Node Spacing Checks

6. **Is there at least 80px vertical gap between rows/layers?**
   - Nodes stacked too close → edges between them have no room for labels

7. **Is there at least 60px horizontal gap between side-by-side nodes?**
   - Nodes too close horizontally → edges routing between them get cramped

8. **Are input nodes ordered to match their target positions?**
   - Input on the left should feed a stage on the left
   - Input on the right should feed a stage on the right
   - If an input would need to cross over another node to reach its target, swap the input positions

## Service Map Specific

9. **Does the page use pageWidth from the layout calculator output?**
   - The calculator may output a page LARGER than 1169px if many services exist

10. **Are there fewer than 12 edges visible on this page?**
    - If more than 12, consider splitting into multiple pages (service map + data flow pages)
    - Too many edges on one page ALWAYS creates overlap

11. **For bidirectional edges: are the two arrows using different exit/entry offsets?**
    - Forward: exitY=0.35, entryY=0.35
    - Reverse: exitY=0.65, entryY=0.65
    - Must be visually distinguishable

## Pipeline Specific

12. **Does the pipeline overview have the annotator rubric as an input?**
    - If the repo has a rubric/config for scoring, it should appear as an input node

13. **Are pass/fail edges colour-coded?**
    - Pass: strokeColor=#82b366 (green)
    - Fail: strokeColor=#b85450 (red)

## Final Sanity

14. **Read through all edge labels one more time. Do any two labels sit in the same visual area?**
    - If yes, remove the less important one (set value="")

15. **Count the total edges on each page. If > 15, you have too many — split into multiple pages.**


## Swimlane/Container Checks

16. **Does each swimlane's height match its content?**
    - Compute: last child y + last child h + 20px = expected height
    - If actual height exceeds expected by more than 60px, shrink it
    - Never leave 100+ px of dead space at the bottom of a swimlane

17. **Are sequential stages stacked vertically (not side-by-side)?**
    - Side-by-side = parallel (run at the same time)
    - Vertical stacking = sequential (one feeds the next)
    - If Fix feeds Re-annotate, they MUST be in separate rows, not side-by-side

18. **Is there at least 40px vertical gap between rows?**
    - Edges between rows need room for labels and arrowheads
    - An edge shorter than 30px will look like floating text

## Layered Architecture Specific

19. **Arrow clearance below band headers: Is there at least 24px between the header bottom and the top of items that receive edges from above?**
    - Header bottom = band_y + startSize
    - Item top must be at header_bottom + 24px minimum
    - If violated: arrowheads get clipped behind the header, arrows appear to start/end in mid-air
    - Fix: move items down, or increase the gap by reducing startSize

20. **Are items receiving cross-layer edges defined as root-level siblings (parent="1"), NOT children of a band?**
    - Children of a band have coordinates relative to the band — entry points resolve incorrectly for edges arriving from outside
    - Root-level siblings use absolute coordinates — edges arrive exactly where expected
    - Only items WITHOUT incoming cross-layer edges should be children (sub-steps, env tool specs)

21. **For horizontal edges between adjacent items: is the gap ≥ 80px if the edge has a label?**
    - Label text width ≈ chars × 6.5 + 8px
    - If "raw blocks" (10 chars) → ~73px. Needs 80px+ gap to not overflow into boxes
    - If gap < 80px: set value="" on the edge and use a separate text annotation cell
    - If gap ≥ 80px: label on the edge is fine

22. **For vertical/dashed edges: does the edge style include `labelPosition=right;align=left;`?**
    - Labels centered on vertical dashed lines break the dash pattern visually
    - Labels must sit to the side of the line, not on top of it
    - Alternative: use a horizontal waypoint jog so the label attaches to a horizontal segment

23. **Does the middle config→pipeline arrow cross through the Pipeline band header text?**
    - Check: is there a straight vertical edge from config area (y < 150) to an item inside pipeline (y > 178)?
    - If yes and the edge has no waypoints to avoid the header zone: it WILL cross through "Pipeline" text
    - Fix: route through the gap with a waypoint at y = gap_midpoint (between config bottom and pipeline top)
    - Or: use band-to-band single arrow (config band → pipeline band) to avoid the problem entirely

24. **Is the gap between Pipeline bottom and Environment top at least 75px?**
    - Dashed env-call edges + their labels need this space
    - Label should sit 30px+ below the module bottom
    - If gap < 75px: labels will crowd against the module or overlap the environment header

25. **Does the Pipeline band header have a fill colour with sufficient contrast (not near-white)?**
    - `#f9f9f9` or `#fafafa` → TOO LIGHT. Edge lines show through even with z-order masking
    - `#f0f0f0` or darker → GOOD. Visually masks any edge segments that pass behind it
    - Coloured bands (yellow, green, purple) are always fine
