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
