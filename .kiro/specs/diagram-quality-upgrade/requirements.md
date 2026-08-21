# Requirements Document

## Introduction

This document defines the requirements for upgrading the drawio-skill to produce multi-level, richly-detailed architecture diagrams. The upgrade introduces hierarchical diagram pages, rich multi-line labels with extracted config values, loop/cycle detection and annotation, N-way conditional routing, extended layout calculator commands, a comprehensive Mermaid companion with subgraph groupings, and per-page validation. The requirements trace directly to the design components: Decomposition Planner, Rich Label Composer, Loop/Cycle Detector, Multi-Page Layout Engine, Data Shape Document Generator, and the extended layout.py calculator.

## Glossary

- **Diagram_Skill**: The overall system that analyzes a repository and generates architecture diagrams
- **Decomposition_Planner**: Component that analyzes the repo model and determines how to split the architecture into multiple diagram pages at different zoom levels
- **Rich_Label_Composer**: Component that extracts specific values from configs, source code, and comments to build multi-line labels
- **Loop_Detector**: Component that identifies iteration patterns (for loops, retry logic, per-item processing) and extracts their bounds
- **Layout_Engine**: Component that computes coordinate positions for all diagram elements across multiple pages
- **Layout_Calculator**: The layout.py Python script that performs arithmetic for coordinate computation
- **XML_Writer**: Component that generates multi-page draw.io XML output
- **Mermaid_Generator**: Component that generates the Mermaid markdown companion document
- **Validator**: Component that checks generated diagrams for edge overlaps, box crossings, and structural consistency
- **RepoModel**: The structured representation of a repository's architecture extracted during exploration
- **DiagramPage**: A single page within the multi-page draw.io output file
- **LoopAnnotation**: A dashed-border visual indicator drawn around nodes that are repeated in a loop
- **NavLink**: A clickable link in the overview page that navigates to a drill-down page
- **DetailLevel**: An enumeration (OVERVIEW, STANDARD, DETAILED) controlling how many label lines a node displays
- **DecisionNode**: A node representing an N-way conditional routing point with multiple outcomes

## Requirements

### Requirement 1: Multi-Page Diagram Decomposition

**User Story:** As a developer, I want the diagram skill to produce a multi-page draw.io file with an overview page and drill-down pages, so that I can navigate complex architectures at different levels of detail.

#### Acceptance Criteria

1. WHEN the Diagram_Skill analyzes a repository, THE Decomposition_Planner SHALL produce exactly one DiagramPage of type OVERVIEW as the first page in the output
2. IF a stage has 3 or more sub-steps or contains at least one loop, THEN THE Decomposition_Planner SHALL create a DRILL_DOWN DiagramPage for that stage
3. THE Decomposition_Planner SHALL ensure every stage in the RepoModel appears in at least one DiagramPage either as a full node or a summary node
4. THE Decomposition_Planner SHALL represent each stage that has a corresponding DRILL_DOWN page as a summary node on the OVERVIEW page, where a summary node displays only the stage title and a one-line description (maximum 2 lines total) and carries a NavLink to the DRILL_DOWN page
5. WHEN the Decomposition_Planner creates a DRILL_DOWN page, THE Decomposition_Planner SHALL create a NavLink from the corresponding summary node on the OVERVIEW page to the DRILL_DOWN page, such that the NavLink references a valid target page_id that exists in the output page set
6. IF the Decomposition_Planner identifies more than 8 drill-down candidates, THEN THE Decomposition_Planner SHALL merge adjacent stages in pipeline order into combined DRILL_DOWN pages (maximum 3 stages per combined page) until the total drill-down page count is 8 or fewer
7. IF the repository has fewer than 3 stages and no stage meets the drill-down threshold defined in criterion 2, THEN THE Decomposition_Planner SHALL produce a single OVERVIEW page where each node uses STANDARD detail level labels (title plus up to 3 lines of config values and file paths)
8. THE Decomposition_Planner SHALL produce no more than 8 DRILL_DOWN pages in the output regardless of repository complexity
9. WHEN the Decomposition_Planner creates a DRILL_DOWN page, THE Decomposition_Planner SHALL include all sub-steps of the corresponding stage as full nodes with DETAILED level labels (title plus up to 5 lines of extracted details)

### Requirement 2: Rich Multi-Line Labels

**User Story:** As a developer, I want diagram nodes to display concrete config values, model names, and file paths, so that I can understand the system without cross-referencing source files.

#### Acceptance Criteria

1. WHEN composing a label at OVERVIEW DetailLevel, THE Rich_Label_Composer SHALL produce at most 2 lines (title plus at most 1 detail line)
2. WHEN composing a label at STANDARD DetailLevel, THE Rich_Label_Composer SHALL produce at most 3 lines (title plus at most 2 detail lines)
3. WHEN composing a label at DETAILED DetailLevel, THE Rich_Label_Composer SHALL produce at most 5 lines (title plus at most 4 detail lines)
4. THE Rich_Label_Composer SHALL truncate any single detail line exceeding 40 characters by cutting at position 37 and appending "..." to produce a final length of exactly 40 characters
5. THE Rich_Label_Composer SHALL escape HTML entities in all label text, replacing < with &lt;, > with &gt;, & with &amp;, and " with &quot;
6. WHEN config values are available for a node, THE Rich_Label_Composer SHALL include extracted config key-value pairs in the label, prioritizing model names first, then temperature/threshold parameters, then file paths
7. WHEN the DetailLevel is DETAILED and source files exist for a node, THE Rich_Label_Composer SHALL include the primary source file path as a relative path in the label
8. IF config values cannot be found for a node, THEN THE Rich_Label_Composer SHALL use a generic label with title and source file path only

### Requirement 3: Loop and Cycle Detection

**User Story:** As a developer, I want loops and retry patterns to be visually annotated on the diagram, so that I can understand iteration behavior and bounds at a glance.

#### Acceptance Criteria

1. WHEN analyzing control flow in orchestrator source files, THE Loop_Detector SHALL identify for-loop patterns, retry patterns, and per-item iteration patterns
2. WHEN a loop is detected, THE Loop_Detector SHALL classify it as one of: FIXED_COUNT, BOUNDED_RANGE, RETRY, PER_ITEM, or UNTIL_CONDITION
3. WHEN iteration bounds are available in config files or code constants, THE Loop_Detector SHALL extract the min_count and max_count values and attach them to the LoopAnnotation
4. IF loop bounds cannot be determined from config or code, THEN THE Loop_Detector SHALL annotate the loop with a label indicating the loop type and unknown count (e.g., "per item" without a specific count, or "repeated N×" where N is unresolved)
5. WHEN a LoopAnnotation with at least one wrapped node is placed on a page, THE Layout_Engine SHALL draw a dashed-border box that fully encloses all wrapped nodes with 15 pixels of padding on each side and 20 additional pixels at the top for the label area
6. THE Layout_Engine SHALL position the loop label at the top-right corner of the annotation box, right-aligned with a 10-pixel inset from the right edge and 5 pixels below the top edge
7. WHEN a LoopAnnotation has bounds, THE Layout_Engine SHALL display the label in the format "[loop context] · [bounds expression]" (e.g., "per turn · repeated 3-7×")
8. IF a LoopAnnotation references wrapped_nodes that do not exist in the current page layout, THEN THE Layout_Engine SHALL skip that annotation and exclude it from the rendered page

### Requirement 4: N-Way Conditional Routing

**User Story:** As a developer, I want decision points to support more than two outcomes, so that diagrams can represent multi-way routing like score thresholds and retry-vs-skip-vs-fail.

#### Acceptance Criteria

1. THE Layout_Engine SHALL support DecisionNodes with 2 to 10 outcomes
2. WHEN laying out an N-way split with more than 2 outcomes, THE Layout_Engine SHALL distribute exit points evenly along the bottom edge of the decision node from position 0.1 to 0.9 using the formula exit_position[i] = 0.1 + (0.8 * i / (N - 1))
3. WHEN laying out an N-way split, THE Layout_Engine SHALL assign each outcome edge its own routing band spaced 10px apart vertically below the decision node bottom edge to prevent edge overlap
4. THE Layout_Engine SHALL label each outcome edge with the outcome condition text, positioned adjacent to the exit point of the edge
5. WHEN a DecisionNode has exactly 2 outcomes, THE Layout_Engine SHALL use exit positions at 0.25 and 0.75 instead of the general distribution formula
6. IF a DecisionNode has fewer than 2 outcomes or more than 10 outcomes, THEN THE Layout_Engine SHALL reject the node with an error message indicating the outcome count is outside the supported range of 2 to 10

### Requirement 5: Extended Layout Calculator

**User Story:** As a developer, I want the layout.py calculator to support nested containers, loop annotations, N-way splits, and multi-page configurations, so that coordinate computation remains deterministic and correct.

#### Acceptance Criteria

1. WHEN the nested-container command is invoked with a parent swimlane width of at least 100 pixels, THE Layout_Calculator SHALL compute child step positions within a container that starts at 12 pixels inset from each side of the parent swimlane, with a 20-pixel header area at the top of the container before the first child
2. WHEN the nested-container command is invoked, THE Layout_Calculator SHALL compute child step width as parent swimlane width minus 36 minus 24 (totaling 60 pixels of combined parent and container padding)
3. WHEN the loop-annotation command is invoked, THE Layout_Calculator SHALL compute an annotation rectangle whose top edge is at first_node_y minus 15 pixels of padding minus 20 pixels for the label area, and whose bottom edge is at last_node_y plus last_node_h plus 15 pixels of padding
4. WHEN the loop-annotation command is invoked, THE Layout_Calculator SHALL compute annotation width as swimlane width minus 8, centered horizontally with 4 pixels of margin on each side within the swimlane
5. WHEN the n-split command is invoked with N outcomes where N is at least 2, THE Layout_Calculator SHALL compute N non-overlapping outcome boxes distributed across the available step width (swimlane width minus 36) with equal gaps of 10 pixels between adjacent boxes, where each box has equal width calculated as (step_width minus (N minus 1) times 10) divided by N rounded down
6. WHEN the multipage command is invoked with page type overview, THE Layout_Calculator SHALL output page dimensions of 827 pixels wide by 1169 pixels tall in portrait orientation
7. WHEN the multipage command is invoked with page type drill_down and the number of parallel swimlanes is 4 or more, THE Layout_Calculator SHALL output page dimensions of 1169 pixels wide by 827 pixels tall in landscape orientation
8. IF the multipage command is invoked with page type drill_down and the number of parallel swimlanes is fewer than 4, THEN THE Layout_Calculator SHALL output page dimensions of 827 pixels wide by 1169 pixels tall in portrait orientation
9. THE Layout_Calculator SHALL require only python3 standard library with no external packages
10. IF any new command (nested-container, loop-annotation, n-split, or multipage) is invoked with fewer arguments than required, THEN THE Layout_Calculator SHALL print a usage message to stderr and exit with a non-zero exit code

### Requirement 6: Rich Mermaid Companion

**User Story:** As a developer, I want the Mermaid companion to include subgraph groupings, rich node labels, and loop annotations, so that the markdown preview provides meaningful architectural context.

#### Acceptance Criteria

1. WHEN generating the Mermaid companion, THE Mermaid_Generator SHALL produce a flowchart TD overview diagram with subgraph blocks grouping related stages
2. WHEN generating drill-down views, THE Mermaid_Generator SHALL include rich node labels with config values extracted from the repository, using the format NodeID["Title\ndetail1\ndetail2"]
3. WHEN loops exist in the architecture, THE Mermaid_Generator SHALL represent loop patterns using Mermaid note annotations or back-edge syntax with a label indicating the loop bounds
4. THE Mermaid_Generator SHALL use valid Mermaid identifiers containing only alphanumeric characters and underscores for all node IDs
5. THE Mermaid_Generator SHALL produce syntactically valid Mermaid markdown that renders without errors in standard Mermaid renderers
6. WHEN data shapes are documented, THE Mermaid_Generator SHALL include a data shape section after the diagrams describing input and output schemas at each stage boundary using markdown tables or JSON code blocks

### Requirement 7: Per-Page Validation

**User Story:** As a developer, I want the validation pass to check every page independently and verify cross-page consistency, so that multi-page diagrams are free of layout errors.

#### Acceptance Criteria

1. WHEN validating a multi-page diagram, THE Validator SHALL check each DiagramPage independently for edge overlaps, where an overlap is defined as two edges sharing a horizontal segment at the same y-coordinate with overlapping x-ranges, or a vertical segment at the same x-coordinate with overlapping y-ranges
2. WHEN validating a multi-page diagram, THE Validator SHALL check each DiagramPage independently for edge-through-box crossings, where a crossing is defined as an edge segment passing through the interior of any vertex that is neither the edge's source nor its target
3. WHEN validating a multi-page diagram, THE Validator SHALL verify that every NavLink references a target page ID that exists in the diagram's page set and that the NavLink source is a valid node on the page containing the link
4. WHEN validating a multi-page diagram, THE Validator SHALL verify that all node IDs are unique across all pages
5. WHEN an edge uses explicit waypoints, THE Validator SHALL verify the last waypoint maintains at least 20 pixels of minimum approach distance in the entry direction, measured from the target vertex boundary along the axis of entry
6. IF validation detects errors on any page, THEN THE Validator SHALL report the page name, the violation type, the offending element IDs, and the coordinates involved, and SHALL prevent the diagram file from being written
7. IF validation completes with no errors detected, THEN THE Validator SHALL report a success summary indicating the total number of edges checked and the number of pages validated

### Requirement 8: Multi-Page XML Generation

**User Story:** As a developer, I want the output draw.io file to contain multiple diagram elements with proper structure, so that draw.io renders each page as a navigable tab.

#### Acceptance Criteria

1. THE XML_Writer SHALL generate one diagram XML element per DiagramPage within a single mxfile element
2. THE XML_Writer SHALL assign a unique id attribute to each diagram element, where uniqueness is scoped to the containing mxfile
3. WHEN a node on the OVERVIEW page has a NavLink, THE XML_Writer SHALL encode the navigation as a link style attribute pointing to the target page
4. THE XML_Writer SHALL ensure all node coordinates are expressed relative to their parent element, where top-level nodes (parent="1") use absolute page coordinates and child nodes within a container use coordinates relative to that container's origin
5. THE XML_Writer SHALL maintain parent-child relationships where steps inside swimlanes use the swimlane ID as parent
6. THE XML_Writer SHALL assign a name attribute to each diagram element using the corresponding DiagramPage name, so that draw.io displays it as the tab label
7. THE XML_Writer SHALL produce well-formed XML that conforms to the mxfile schema structure (mxfile > diagram > mxGraphModel > root > mxCell elements)

### Requirement 9: Security and Privacy

**User Story:** As a developer, I want the diagram skill to exclude secrets from labels and use relative paths, so that generated diagrams are safe to share.

#### Acceptance Criteria

1. WHEN extracting config values, THE Rich_Label_Composer SHALL perform case-insensitive filtering and omit any key-value pair whose key ends in _KEY, _SECRET, _TOKEN, _PASSWORD, _CREDENTIAL, or exactly matches (case-insensitive) password, secret, token, or api_key
2. WHEN a config key-value pair is filtered as a secret, THE Rich_Label_Composer SHALL exclude the entire entry from the label without displaying the key name or value
3. THE Rich_Label_Composer SHALL express all file paths in labels as relative to the repository root directory and SHALL NOT include path segments that begin with a user home directory prefix such as /Users/, /home/, C:\Users\, or the ~ character
4. THE Diagram_Skill SHALL read but never execute code from the target repository

### Requirement 10: Graceful Degradation

**User Story:** As a developer, I want the diagram skill to produce useful output even when information is incomplete, so that partial analysis still yields a meaningful diagram.

#### Acceptance Criteria

1. IF config values are unavailable for a node, THEN THE Rich_Label_Composer SHALL fall back to a label containing only the title and source file path
2. IF loop bounds are unknown, THEN THE Loop_Detector SHALL annotate with the loop type label followed by "repeated N×" where N indicates the count is unresolved
3. IF a nested container exceeds 2 levels of depth, THEN THE Layout_Engine SHALL flatten excess depth into multi-line labels with a "..." truncation indicator appended to the last visible line
4. IF the repository has fewer than 3 stages and no stage meets the drill-down threshold, THEN THE Decomposition_Planner SHALL produce a single enhanced OVERVIEW page where nodes use STANDARD detail level labels
5. IF both config values and source file paths are unavailable for a node, THEN THE Rich_Label_Composer SHALL produce a single-line label containing only the node title
