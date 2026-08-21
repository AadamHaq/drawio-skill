# Implementation Plan: Microservice Topology Support

## Overview

This plan extends the drawio-skill with microservice topology support. Implementation is split into: (1) new layout.py commands for service-map coordinate computation, (2) SKILL.md extensions for topology classification, service discovery, and service-map rendering instructions, (3) diagram-validate SKILL.md updates for new page types, and (4) documentation updates. All changes to `claude/` must be mirrored identically to `kiro/`.

## Tasks

- [ ] 1. Add service-map layout commands to layout.py
  - [ ] 1.1 Implement `cmd_service_map` command
    - Add the `service-map <n_services>` command that computes grid positions for N services on a landscape page (1169×827)
    - Implement layer assignment logic (client, gateway, service, worker, infrastructure) based on service index hints
    - Output: page_w, page_h, orientation, grid_cols, grid_rows, and per-service x/y/w/h positions
    - Add to dispatch table in `main()`
    - Modify both `claude/skills/diagram/layout.py` and `kiro/skills/diagram/layout.py` (identical content)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1_

  - [ ] 1.2 Implement `cmd_service_container` command
    - Add the `service-container <n_components> [container_w]` command that computes internal layout for a service container
    - Output: container_w, container_h, and per-component x/y/w/h slot positions
    - Default container_w=180, component height=24, header=30, padding=10
    - Add to dispatch table in `main()`
    - Modify both `claude/skills/diagram/layout.py` and `kiro/skills/diagram/layout.py`
    - _Requirements: 8.2_

  - [ ] 1.3 Implement `cmd_bidirectional_edge` command
    - Add the `bidirectional-edge <src_x> <src_y> <src_w> <src_h> <tgt_x> <tgt_y> <tgt_w> <tgt_h> [offset]` command
    - Compute forward and reverse edge exit/entry points with parallel offset
    - Determine dominant direction (horizontal vs vertical) and apply perpendicular offset
    - Output: forward exitX/exitY/entryX/entryY and reverse exitX/exitY/entryX/entryY
    - Add to dispatch table in `main()`
    - Modify both `claude/skills/diagram/layout.py` and `kiro/skills/diagram/layout.py`
    - _Requirements: 4.1, 4.2, 4.3, 8.3_

  - [ ] 1.4 Implement `cmd_conditional_group` command
    - Add the `conditional-group <x1,y1,w1,h1> <x2,y2,w2,h2> ...` command (minimum 2 service positions)
    - Compute dashed bounding box with padding (default 20px) enclosing all specified services
    - Include extra top space for label area
    - Output: group_x, group_y, group_w, group_h, label_x, label_y
    - Add to dispatch table in `main()`
    - Modify both `claude/skills/diagram/layout.py` and `kiro/skills/diagram/layout.py`
    - _Requirements: 5.1, 5.2, 5.3, 8.4_

  - [ ] 1.5 Extend `cmd_multipage` to support new page types
    - Add `service_map` and `deployment` to valid page types
    - `service_map`: landscape orientation (1169×827)
    - `deployment`: landscape orientation (1169×827)
    - Update usage string in module docstring
    - Modify both `claude/skills/diagram/layout.py` and `kiro/skills/diagram/layout.py`
    - _Requirements: 6.2, 8.1_

  - [ ] 1.6 Write property tests for `cmd_service_map`
    - **Property 6: No-Overlap and Page Containment**
    - For N in [1, 15], verify all bounding boxes are non-overlapping and within page bounds
    - **Validates: Requirements 7.1, 7.2**

  - [ ] 1.7 Write property tests for `cmd_bidirectional_edge`
    - **Property 7: Bidirectional Edge Separation**
    - For arbitrary non-overlapping source/target positions, verify two paths separated by 2×offset and non-overlapping
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [ ] 1.8 Write property tests for `cmd_conditional_group`
    - **Property 8: Conditional Group Containment**
    - For any set of 2+ service positions, verify bounding box contains all services with padding
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [ ] 2. Checkpoint - Verify layout.py commands
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Add topology classification and service discovery instructions to SKILL.md
  - [ ] 3.1 Add topology classification section to Step 1 (Explore)
    - Insert new subsection after the existing Step 1 exploration questions
    - Define the topology classifier signals (pipeline vs microservice indicators)
    - Document signal weights and classification decision rules
    - Define output format: topology type, confidence, service list
    - Specify default-to-PIPELINE fallback when confidence is low
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 11.3, 11.4_

  - [ ] 3.2 Add service discovery section (new Step 1b)
    - Define how to scan docker-compose, k8s manifests, Helm charts, Tiltfiles, and service directories
    - Specify how to extract service name, path, runtime type, components, ports, dependencies
    - Define inference fallback when no infrastructure config is found
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 2.1, 2.2, 2.4_

  - [ ] 3.3 Add communication edge mapping section (new Step 1c)
    - Define how to detect HTTP client calls, gRPC stubs, WebSocket connections, pub/sub patterns
    - Document bidirectional collapse rules (A→B + B→A = single bidi edge)
    - Document deduplication rules (no duplicate source/target/protocol triples)
    - Document conditional edge annotation (mode-dependent edges)
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 3.4 Add conditional mode detection section (new Step 1d)
    - Define how to detect configuration-selected subgraphs from env vars and config switches
    - Document mode structure: name, config_key, services list, edges list
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 5.1, 5.3_

- [ ] 4. Add service-map page planning and layout instructions to SKILL.md
  - [ ] 4.1 Extend Step 2 (Plan Decomposition) with topology-aware page planning
    - Add rules for MICROSERVICE topology: generate SERVICE_MAP + optional DEPLOYMENT + DATA_FLOW per mode
    - Add rules for HYBRID topology: generate both pipeline pages and service-map pages
    - Add rules for conditional modes: separate DATA_FLOW pages per mode
    - Specify >15 services grouping strategy (cluster into logical groups, split pages)
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 11.1_

  - [ ] 4.2 Add service-map layout instructions (new Step 3b)
    - Document layered grid layout: clients top, gateways second, services middle, workers lower, infra bottom
    - Document horizontal distribution within layers with consistent spacing
    - Document edge-crossing minimization via within-layer swaps
    - Reference `layout.py service-map` and `layout.py service-container` commands
    - Handle cycle-breaking for layout (render all edges, but use DAG for layer assignment)
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 11.2_

  - [ ] 4.3 Add service-map visual styles and edge rules (new Step 5b / Step 6b)
    - Document service container style (rounded rectangle, swimlane header, fill color)
    - Document infrastructure node style (cylinder shape)
    - Document protocol-colored edge styles (HTTP=blue, gRPC=purple, WS=orange-dashed, pubsub=green-dashed)
    - Document bidirectional edge rendering (two parallel offset arrows, reference `layout.py bidirectional-edge`)
    - Document conditional group boundary style (dashed, reduced opacity)
    - Document node shapes by runtime type (always_running, one_shot, triggered, infrastructure, external, client)
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 4.1, 4.2_

  - [ ] 4.4 Add service-map XML template (extend Step 7)
    - Document the XML structure for SERVICE_MAP and DEPLOYMENT page types
    - Show example mxCell elements for service containers, infrastructure nodes, protocol-colored edges
    - Show example conditional group boundary with dashed style
    - Reference `layout.py multipage service_map` for page dimensions
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 6.2, 8.1, 9.1, 9.2, 9.3, 9.4_

- [ ] 5. Checkpoint - Verify SKILL.md updates
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Add secrets filtering for service-map labels
  - [ ] 6.1 Add service-map specific secrets filtering instructions to SKILL.md
    - Extend the existing "Secret Filtering" section to cover service-map labels
    - Add rule for stripping credentials from infrastructure connection strings in docker-compose/k8s
    - Add rule for excluding env vars matching secret patterns from node labels
    - Modify both `claude/skills/diagram/SKILL.md` and `kiro/skills/diagram/SKILL.md`
    - _Requirements: 12.1, 12.2, 12.3_

- [ ] 7. Update diagram-validate SKILL.md with service-map validation rules
  - [ ] 7.1 Add service-map validation checks
    - Add check: service containers must have at least a name and one port in their label
    - Add check: conditional group boundaries must reference at least 2 services
    - Add check: bidirectional edges must not overlap (verify parallel offset)
    - Add check: all edges must use protocol-appropriate colors
    - Add check: SERVICE_MAP pages must use landscape orientation (1169×827)
    - Modify both `claude/skills/diagram-validate/SKILL.md` and `kiro/skills/diagram-validate/SKILL.md`
    - _Requirements: 5.3, 9.3_

- [ ] 8. Verify backward compatibility
  - [ ] 8.1 Write backward compatibility tests for existing layout.py commands
    - Verify all existing commands (swimlanes, inputs, outputs, steps, split, check-approach, nested-container, loop-annotation, n-split, multipage) produce unchanged output for the same arguments
    - Add regression test cases using known input/output pairs from current behavior
    - Run existing test suite (tests/test_layout.py, tests/test_property_*.py) to confirm no regressions
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ] 8.2 Write property test for backward compatibility
    - **Property 1: Backward Compatibility**
    - For any valid arguments to existing commands, output must match pre-feature behavior
    - **Validates: Requirements 1.2, 10.1, 10.2, 10.3**

- [ ] 9. Update README.md documentation
  - [ ] 9.1 Update README.md with microservice topology documentation
    - Document the new topology classification behavior
    - Document new layout.py commands (service-map, service-container, bidirectional-edge, conditional-group)
    - Document new page types (SERVICE_MAP, DEPLOYMENT)
    - Document new visual styles and protocol-colored edges
    - Note backward compatibility guarantee for pipeline repos
    - _Requirements: 1.1, 8.1, 8.2, 8.3, 8.4_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All file modifications must be applied identically to both `claude/` and `kiro/` directories
- The implementation language is Python for layout.py and Markdown for SKILL.md files
- No third-party dependencies are allowed — layout.py remains zero-dependency Python

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5"] },
    { "id": 1, "tasks": ["1.6", "1.7", "1.8", "3.1", "3.2", "3.3", "3.4"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "6.1"] },
    { "id": 3, "tasks": ["7.1", "8.1"] },
    { "id": 4, "tasks": ["8.2", "9.1"] }
  ]
}
```
