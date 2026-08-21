# Implementation Plan: Diagram Quality Upgrade

## Overview

This plan upgrades the drawio-skill to produce multi-level, richly-detailed architecture diagrams. The implementation extends layout.py with new coordinate commands (nested-container, loop-annotation, n-split, multipage), updates SKILL.md with multi-page decomposition planning, rich label composition, loop detection, and N-way routing instructions, updates diagram-validate SKILL.md for multi-page validation, and adds rich Mermaid companion generation. Each file pair (claude/ and kiro/) is kept identical.

## Tasks

- [x] 1. Extend layout.py with new calculator commands
  - [x] 1.1 Implement `cmd_nested_container` command in `claude/skills/diagram/layout.py`
    - Add function that accepts parent_sw_w, parent_start_y, n_children, and lines_per_child arguments
    - Compute container dimensions: container_x=12, container_w=parent_sw_w-24, child_step_w=parent_sw_w-60
    - Compute each child position with 20px header area, 16px gaps, and height formula max(36, 22 + lines × 18)
    - Print container_x, container_y, container_w, child_step_w, child_step_x, child positions, and container_h
    - Validate parent_sw_w >= 100, print usage to stderr and exit non-zero if fewer args than required
    - _Requirements: 5.1, 5.2, 5.10_

  - [x] 1.2 Implement `cmd_loop_annotation` command in `claude/skills/diagram/layout.py`
    - Add function that accepts first_node_y, last_node_y, last_node_h, and sw_w arguments
    - Compute annotation_y = first_node_y - 15 (padding) - 20 (label area)
    - Compute annotation_bottom = last_node_y + last_node_h + 15
    - Compute annotation_w = sw_w - 8 (4px margin each side), annotation_x = 4
    - Compute label_x = annotation_x + annotation_w - 10, label_y = annotation_y + 5
    - Print annotation_x, annotation_y, annotation_w, annotation_h, label_x, label_y
    - Validate all args are positive integers, print usage to stderr and exit non-zero if invalid
    - _Requirements: 5.3, 5.4, 5.10_

  - [x] 1.3 Implement `cmd_n_split` command in `claude/skills/diagram/layout.py`
    - Add function that accepts sw_w, last_step_y, last_step_h, n_outcomes, and optional split_gap (default 50)
    - Compute step_w = sw_w - 36, split_y = last_step_y + last_step_h + split_gap
    - Compute box_w = floor((step_w - (n-1)*10) / n) for each outcome box
    - Compute each outcome x position: x[i] = 18 + i * (box_w + 10)
    - Print split_y, and for each outcome: x, w
    - Print sl_height = split_y + 36 + 20
    - Validate n_outcomes >= 2, print usage to stderr and exit non-zero if invalid
    - _Requirements: 5.5, 5.10_

  - [x] 1.4 Implement `cmd_multipage` command in `claude/skills/diagram/layout.py`
    - Add function that accepts page_type and optional n_swimlanes argument
    - For "overview": output page_w=827, page_h=1169, orientation=portrait
    - For "drill_down" with n_swimlanes >= 4: output page_w=1169, page_h=827, orientation=landscape
    - For "drill_down" with n_swimlanes < 4: output page_w=827, page_h=1169, orientation=portrait
    - Print page_w, page_h, orientation
    - Validate page_type is one of overview/drill_down/data_flow, print usage to stderr and exit non-zero if invalid
    - _Requirements: 5.6, 5.7, 5.8, 5.10_

  - [x] 1.5 Update `main()` dispatch table and module docstring in `claude/skills/diagram/layout.py`
    - Add nested-container, loop-annotation, n-split, and multipage to the dispatch dictionary
    - Update the module docstring to document all new commands and their argument signatures
    - _Requirements: 5.9, 5.10_

  - [x] 1.6 Copy updated `claude/skills/diagram/layout.py` to `kiro/skills/diagram/layout.py`
    - Ensure both files are byte-for-byte identical
    - _Requirements: 5.1–5.10_

  - [x]* 1.7 Write unit tests for new layout.py commands
    - Test nested-container with varying parent widths and child counts
    - Test loop-annotation with edge cases (single node, many nodes)
    - Test n-split with 2, 3, 5, and 10 outcomes
    - Test multipage with overview and drill_down page types
    - Test error handling: insufficient args, invalid values
    - _Requirements: 5.1–5.10_

  - [x]* 1.8 Write property test: nested container containment
    - **Property 10: Nested Container Containment**
    - For any parent_sw_w >= 100 and any number of children, verify child positions fit within parent bounds and child_step_w == parent_sw_w - 60
    - **Validates: Requirements 5.1, 5.2**

  - [x]* 1.9 Write property test: n-split box coverage
    - **Property 11: N-Split Box Coverage**
    - For any N >= 2 and any step_width, verify N non-overlapping outcome boxes whose combined widths plus gaps fill the available step_width
    - **Validates: Requirements 5.5**

  - [x]* 1.10 Write property test: loop enclosure
    - **Property 8: Loop Enclosure**
    - For any first_node_y, last_node_y, last_node_h, and sw_w, verify the annotation rectangle fully contains the node range with >= 15px padding on all sides
    - **Validates: Requirements 5.3, 5.4**

- [x] 2. Checkpoint - Verify layout.py
  - Ensure all layout.py commands run correctly with sample inputs, ask the user if questions arise.

- [x] 3. Update SKILL.md with multi-page decomposition and rich labels
  - [x] 3.1 Add multi-page decomposition planning section to `claude/skills/diagram/SKILL.md`
    - Insert new Step 1.5 (between Explore and Plan): "Plan Decomposition Levels"
    - Document the rules: always create overview page, drill-down for stages with >= 3 sub-steps or loops
    - Document max 8 drill-down pages, adjacent stage merging when > 8 candidates
    - Document summary node format (title + 1-line description, NavLink to drill-down)
    - Document single-page fallback for simple repos (< 3 stages, no drill-down threshold met)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 3.2 Add rich label composition instructions to `claude/skills/diagram/SKILL.md`
    - Document DetailLevel rules: OVERVIEW (max 2 lines), STANDARD (max 3), DETAILED (max 5)
    - Document config value extraction and priority order: model names > thresholds > file paths
    - Document 40-character truncation rule (cut at 37, append "...")
    - Document HTML entity escaping requirements (<, >, &, ")
    - Document secret filtering: omit keys ending in _KEY, _SECRET, _TOKEN, _PASSWORD, _CREDENTIAL or matching password/secret/token/api_key
    - Document relative path only requirement (no /Users/, /home/, C:\Users\, ~)
    - Document fallback rules when config values unavailable
    - _Requirements: 2.1–2.8, 9.1, 9.2, 9.3, 10.1, 10.5_

  - [x] 3.3 Add loop detection and annotation instructions to `claude/skills/diagram/SKILL.md`
    - Document loop classification types: FIXED_COUNT, BOUNDED_RANGE, RETRY, PER_ITEM, UNTIL_CONDITION
    - Document how to extract loop bounds from config/code constants
    - Document loop annotation visual: dashed-border box, 15px padding, 20px label area at top
    - Document label format: "[loop context] · [bounds expression]" at top-right
    - Document fallback for unknown bounds
    - Document instruction to call `layout.py loop-annotation` for coordinate calculation
    - _Requirements: 3.1–3.8, 10.2_

  - [x] 3.4 Add N-way conditional routing instructions to `claude/skills/diagram/SKILL.md`
    - Replace the current binary pass/fail split section with generalized N-way routing
    - Document exit point distribution formula: exit_position[i] = 0.1 + (0.8 * i / (N-1))
    - Document special case for 2 outcomes: exit at 0.25 and 0.75
    - Document routing bands: 10px apart vertically below decision node
    - Document outcome edge labeling requirements
    - Document instruction to call `layout.py n-split` for coordinate calculation
    - Document 2–10 outcome range constraint
    - _Requirements: 4.1–4.6, 10.3_

  - [x] 3.5 Add multi-page XML generation instructions to `claude/skills/diagram/SKILL.md`
    - Update Step 6 (XML structure) to show multi-page mxfile with multiple `<diagram>` elements
    - Document unique id per diagram element, name attribute for tab labels
    - Document NavLink encoding as link style attribute
    - Document relative coordinates within containers, parent-child relationships
    - Document page dimension settings (portrait vs landscape via multipage command)
    - Show example multi-page XML structure
    - _Requirements: 8.1–8.7_

  - [x] 3.6 Update Mermaid companion section in `claude/skills/diagram/SKILL.md`
    - Replace Step 8 with rich Mermaid generation including subgraph blocks
    - Document flowchart TD with subgraph groupings for related stages
    - Document rich node label format: NodeID["Title\ndetail1\ndetail2"]
    - Document loop representation using note annotations or back-edge syntax
    - Document valid Mermaid identifier rules (alphanumeric + underscore only)
    - Document data shape section with markdown tables or JSON code blocks
    - _Requirements: 6.1–6.6_

  - [x] 3.7 Add security instructions section to `claude/skills/diagram/SKILL.md`
    - Document that the skill SHALL read but never execute code from the target repo
    - Cross-reference secret filtering rules from label composition section
    - _Requirements: 9.4_

  - [x] 3.8 Copy updated `claude/skills/diagram/SKILL.md` to `kiro/skills/diagram/SKILL.md`
    - Ensure both files are byte-for-byte identical
    - _Requirements: 1.1–10.5_

- [x] 4. Checkpoint - Verify SKILL.md coherence
  - Ensure the SKILL.md reads as a coherent end-to-end instruction set, ask the user if questions arise.

- [x] 5. Update diagram-validate SKILL.md for multi-page validation
  - [x] 5.1 Add multi-page validation logic to `claude/skills/diagram-validate/SKILL.md`
    - Update the "What to check" section to iterate over each `<diagram>` element independently
    - Document per-page edge overlap checking
    - Document per-page edge-through-box crossing checking
    - Document NavLink validation: every link target must reference an existing page ID, source must be valid node on containing page
    - Document unique node ID check across all pages
    - Document minimum approach distance validation (20px) for edges with explicit waypoints
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 5.2 Update validation output format in `claude/skills/diagram-validate/SKILL.md`
    - Update error reporting to include page name, violation type, element IDs, and coordinates
    - Document that validation failure SHALL prevent the diagram file from being written
    - Document success summary format: total edges checked and pages validated
    - _Requirements: 7.6, 7.7_

  - [x] 5.3 Copy updated `claude/skills/diagram-validate/SKILL.md` to `kiro/skills/diagram-validate/SKILL.md`
    - Ensure both files are byte-for-byte identical
    - _Requirements: 7.1–7.7_

- [x] 6. Update README.md documentation
  - [x] 6.1 Update `README.md` to document new capabilities
    - Document multi-page diagram output with overview + drill-down pages
    - Document rich labels with config values and file paths
    - Document loop/cycle annotations
    - Document N-way conditional routing
    - Document new layout.py commands with usage examples
    - Document multi-page validation
    - Document rich Mermaid companion with subgraphs and data shapes
    - _Requirements: 1.1–10.5_

- [x] 7. Final checkpoint - End-to-end review
  - Ensure all files are consistent, both claude/ and kiro/ directories match, and the skill instructions form a coherent workflow. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The claude/ and kiro/ directories must always contain identical file content
- This is a skill/prompt repo — "implementation" means writing Python (layout.py) and Markdown (SKILL.md) instructions

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4"] },
    { "id": 1, "tasks": ["1.5"] },
    { "id": 2, "tasks": ["1.6", "1.7", "1.8", "1.9", "1.10"] },
    { "id": 3, "tasks": ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7"] },
    { "id": 4, "tasks": ["3.8", "5.1"] },
    { "id": 5, "tasks": ["5.2"] },
    { "id": 6, "tasks": ["5.3", "6.1"] }
  ]
}
```
