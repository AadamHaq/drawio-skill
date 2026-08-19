# Improvement Plan — Next Session

## Context

Tested the skill against 3 repos (auto-eval, convai-lab, convai). Key findings:
- **convai** (microservice): Page 2 has overlapping steps (hard bug), page 1 has "funny arrows" (routing issues, dense edges)
- **convai-lab** (layered): Structurally correct but informationally empty — filenames with 2-word descriptions don't help anyone
- **auto-eval** (layered): Best of three but page is oversized, lacking detail on models/thresholds, and arrows between modules are awkward (35px gaps)

## Priority Order

### Phase 1: Fix Hard Bugs (prevent broken output)

1. **Enforce `layout.py steps` usage — prevent step overlap**
   - File: `SKILL.md`, `pipeline/render.md`, `layered/render.md`
   - Add: "NEVER manually compute step y-positions. ALWAYS run `layout.py steps <sw_w> <startSize> <lines...>` and use the output directly. Manual placement causes overlap."
   - Why: convai page 2 has df-step5 and df-step6 overlapping by 20px because the agent eyeballed positions

2. **Enforce minimum sibling gap (50px)**
   - File: `layered/render.md`, `layout.py`
   - Add to layers command: warn if computed item width + gaps would produce <50px between items
   - Add to render.md: "Minimum 50px horizontal gap between sibling items. Reduce item width if needed."
   - Why: auto-eval has 35px gen→val gap, making horizontal edges and labels impossible to read

3. **Require waypoints for ALL cross-band edges**
   - File: `layered/render.md`
   - Add: "Every cross-layer edge MUST have at least one waypoint in the gap between bands (y = source_band_bottom + gap/3). Never draw a straight line from one band's content to another band's content — it will cross the intermediate band's header."
   - Why: auto-eval e-cfg-val goes straight through Pipeline header

4. **Fix validate.py for layered topology**
   - File: `validate.py`
   - Add: auto-detect layered topology (multiple full-width swimlanes at root level) and suppress BOX CROSSING for background bands
   - Add: detect step overlap within same parent (if step[n].y + step[n].h > step[n+1].y → error)
   - Add: flag duplicate edge labels on same page
   - Why: 23 false positives drown out real issues; step overlap should be caught

### Phase 2: Fix Content Quality (make diagrams informative)

5. **Add richness requirements to explore.md output**
   - File: `explore.md`
   - Expand the "Output of this step" section to require:
     - Specific model names/versions for each module
     - Key thresholds and parameters (batch sizes, score gates, retry counts)
     - Output file locations/formats
     - The orchestrator script name and its step numbering
   - Why: convai-lab labels are just "sweep.py / matrix driver" — useless

6. **Add content-richness rules to all render strategies**
   - Files: `pipeline/render.md`, `layered/render.md`, `microservice/render.md`
   - Add: "Sub-labels MUST explain what the component DOES, not just its name. Bad: 'sweep.py / matrix driver'. Good: 'sweep.py / iterates model×arm×dataset, launches per-cell eval'"
   - Add: "Every box should contain information a new engineer couldn't guess from the title alone"
   - Why: all three diagrams have boxes that are just filenames with generic descriptions

7. **Add drill-down page guidance for layered topology**
   - File: `layered/render.md`
   - Add: "If any module in the middle layer has ≥3 sub-steps, produce a drill-down page for it (same rules as pipeline drill-downs). Show internal flow, specific models used per step, parameters."
   - Why: auto-eval's Generator has 5 detailed steps but no page 2 to show them properly

8. **Edge label length: preserve function/method names**
   - File: `edge-rules.md`
   - Change: "12 char max" → "12 char max for generic labels. Preserve function names as-is up to 20 chars (e.g., execute_tool(), validate_call()). If still too long, use the verb only."
   - Why: "execute" is less useful than "execute_tool()"

### Phase 3: Fix Rendering Quality (make diagrams pretty)

9. **Page size: custom page dimensions to fit content**
   - Files: `layered/render.md`, `pipeline/render.md`, `microservice/render.md`, `SKILL.md`
   - Instead of fixed A4 (827×1169 or 1169×827), compute page dimensions from actual content:
     ```
     page_w = max(content_right + 40, 600)   # minimum 600px wide
     page_h = lowest_element_bottom + legend_h + 60
     ```
   - Set these in `<mxGraphModel pageWidth="..." pageHeight="...">` 
   - Add to Step 5 (Render): "After placing all nodes, compute page dimensions. Set pageWidth/pageHeight to tightly fit the content with 40px margins. Do NOT use default A4 dimensions."
   - Optionally add a `layout.py page-size <lowest_y> <rightmost_x>` helper
   - Why: auto-eval uses 1169px height for ~940px of content. Custom size = no dead space in draw.io editor AND tighter SVG viewBox.

9b. **Convai SVG does not render in Kiro editor**
   - File: `render_svg.py`
   - The multi-page convai SVG (2 pages concatenated with `<!-- Page N -->` comments) does not display in Kiro's built-in image preview
   - Root cause: likely the concatenated multi-SVG format (two `<svg>` root elements in one file) is invalid. Only one `<svg>` root is allowed per file.
   - Fix options:
     a. Output separate files: `architecture_p1.svg`, `architecture_p2.svg`
     b. Wrap in a single SVG with nested `<svg>` elements (each page as a positioned sub-SVG)
     c. Only output page 1 as the SVG (service map / overview) and note that page 2 requires opening the .drawio
   - Recommendation: Option (a) — separate files per page. Simple, always valid, editor-compatible.

10. **Service map edge density / routing**
    - File: `microservice/render.md`
    - Add: "If two edges would carry the same label (e.g., 'completions' twice), differentiate them: 'text comp' and 'voice comp'. Reader must know which is which."
    - Add: "Edges with waypoints that jog through narrow gaps (<20px from a header or box border) should be rerouted with more clearance."
    - Why: convai has duplicate "completions" and awkward near-header routing

11. **Data flow page: use layout.py steps strictly**
    - File: `microservice/render.md` (data flow section)
    - Add: "Data flow swimlane steps MUST be computed with `layout.py steps`. Copy the output y-positions directly. Do not adjust manually."
    - Reinforce with example showing the command and how to use its output
    - Why: convai page 2 step overlap

12. **Improve SVG renderer for service maps**
    - File: `render_svg.py`
    - Fix: orthogonal routing for side-exit edges (exitX=0/1) that cross multiple layers — current mid_x approach creates awkward S-bends
    - Fix: edges from infrastructure layer (bottom) going up to service layer need proper Z-routing
    - Why: convai page 1 "funny arrows"

### Phase 4: Validation & Testing (ensure quality stays)

13. **Add automated content-quality check to validate.py**
    - New check: "If a vertex has only a filename with no description line (no `<br/>`), warn: TOO THIN"
    - New check: "If a swimlane with sub-steps has no edge connecting to another swimlane, warn: ISOLATED MODULE"
    - New check: "If page uses default 1169px height but content bottom < 900px, warn: OVERSIZED PAGE"
    - Why: catches thin content and wasted space before the user sees the output

14. **Re-test all three repos after fixes**
    - Re-run skill on auto-eval, convai-lab, convai
    - Compare output to these notes
    - Target: zero P1 issues, ≤2 P2 issues, all boxes have 2+ lines of meaningful text

## Summary

| Phase | Tasks | Impact |
|-------|-------|--------|
| 1: Hard Bugs | #1–#4 | Prevents broken output (overlaps, invisible arrows, false alarms) |
| 2: Content | #5–#8 | Makes diagrams actually useful (not just pretty boxes with filenames) |
| 3: Rendering | #9–#12 | Makes diagrams look professional (proper sizing, clean arrows, valid SVGs) |
| 4: Testing | #13–#14 | Ensures improvements stick across future uses |
