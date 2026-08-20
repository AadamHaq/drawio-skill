# Improvement Plan — Round 3

## Context (from v2 test output)

Content richness is now good (model names, thresholds, specific descriptions). But:
- Text overflows boxes in all 3 diagrams (content too long for box widths)
- Module gaps are too narrow (25px auto-eval, 40px convai-lab vs 50px rule)
- Arrows entering swimlanes are hidden behind headers (z-order) — the header masking is correct for edges CROSSING through, but arrows actually ENTERING the swimlane should be visible. The fix we did before was to position child items below the header with 24px clearance, but the agents aren't consistently doing this.

## Priority Order

### Phase 1: Text Fits In Box (most visible issue)

1. **Add a character-per-line rule to all render strategies**
   - Files: `pipeline/render.md`, `layered/render.md`, `microservice/render.md`
   - Rule: "Max characters per line = (box_width - 12) / 5.5. For a 200px box: max 34 chars. For a 270px box: max 47 chars."
   - Add: "If your description text won't fit, either widen the box OR abbreviate. Check EVERY box."
   - Add: "Use `layout.py step-height` to compute box height from actual line count."

2. **Add a `layout.py text-width` helper**
   - Computes minimum box width from a label: `text-width "my label text<br/>second line"`
   - Output: `min_width=N` (computed as max_line_length * 5.5 + 12)
   - The agent can call this before placing boxes to ensure they'll fit.

3. **Update `layout.py layers` to support wider default items**
   - Currently items are capped at 200px. For repos with detailed labels, this is too narrow.
   - Auto-widen the page if items won't fit with 50px gaps at the needed width.
   - Default item width: 240px (fits ~41 chars) unless page would exceed 1200px.

### Phase 2: Gap Enforcement

4. **Auto-eval: widen page for 4+ modules**
   - With 4 modules in a row, a standard 827px page can't fit 50px gaps + readable boxes.
   - Add to layered/render.md: "If you have 4+ modules in a row, use a wider page (1000-1200px) to maintain 50px+ gaps at 200px+ module width."
   - Update `layout.py layers` to auto-widen when items won't fit.

5. **Update layers command to enforce minimum gap**
   - If computed gap < 50px, auto-increase page width until gap >= 50.
   - Print a warning: "page widened to {new_w} to maintain 50px gaps"

### Phase 3: Arrow Visibility (entry into swimlanes)

6. **Enforce 24px+ clearance below swimlane headers for child items**
   - Files: `layered/render.md`, `pipeline/render.md`
   - Make it LOUDER: "FIRST CHILD y-position inside a swimlane = startSize + 26. NEVER less. This ensures arrows entering the swimlane are visible between the header bar and the first content box."
   - Currently agents use startSize + 6 or startSize + 12 — not enough.

7. **Update scaffold command to use correct clearance**
   - `layout.py scaffold` currently places steps at startSize + 15.
   - Change to startSize + 26.

8. **render_svg.py: Headers should not cover edges that TARGET this swimlane**
   - Currently ALL swimlane headers render after ALL edges.
   - This is correct for edges CROSSING through the header zone.
   - But for edges whose TARGET is this swimlane (or a child inside it), the arrow should be visible entering the swimlane. The header should NOT cover those.
   - Fix approach: when building the header z-layer, for each header check which edges target this swimlane. Render those edges AFTER the header (in a "foreground edges" pass).
   - OR (simpler, docs-only fix): the skill should target the first child inside the swimlane, not the swimlane itself. Then the arrow terminates below the header naturally.
   - **Recommended**: Both. Docs say "target first child" AND renderer handles the case where someone targets the parent.

### Phase 4: Minor Fixes

9. **Output box heights: enforce step-height usage**
   - gen-out/post-out are 32px for 2 lines (need 36px).
   - Add to render guides: "ALWAYS compute box height with `layout.py step-height 'line1<br/>line2'`"

10. **Suppress false positives for service container children**
    - validate.py flags 4px gaps inside service containers.
    - These are stacked labels (no arrows between them), not sequential steps.
    - Fix: only flag tight gaps if there are edges between the children.

11. **Add text-overflow check to validate.py**
    - New check: estimate text width per line (chars * 5.5 + 12) vs box width.
    - Flag: "TEXT OVERFLOW: '{id}' line '{line}' is ~{est}px in a {w}px box"
    - This catches the problem BEFORE the user sees it.

## Summary

| Phase | Impact |
|-------|--------|
| 1: Text fits | Boxes are wide enough for their content — no clipping in draw.io or SVG |
| 2: Gaps | Modules don't crowd each other — horizontal edges + labels have room |
| 3: Arrows | Arrows entering swimlanes are visible — not hidden behind headers |
| 4: Minor | Correct heights, fewer false positives, overflow detection |
