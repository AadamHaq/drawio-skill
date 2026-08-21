# Requirements Document

## Introduction

This document specifies the requirements for adding microservice and distributed system topology support to the drawio-skill. The feature introduces a topology classifier that determines whether a repository follows a pipeline, microservice, or hybrid architecture, and branches diagram generation accordingly. Microservice repos receive a new service-map strategy with dedicated layout commands, visual styles, and page types, while pipeline repos continue to produce identical output to the current system.

## Glossary

- **Topology_Classifier**: The component that analyzes repository signals and determines whether the repo is a pipeline, microservice, or hybrid architecture
- **Service_Discovery**: The component that performs deep analysis of a microservice repo to extract services, communication edges, and conditional topologies
- **Layout_Engine**: The layout.py Python script that computes coordinates for diagram elements
- **Communication_Edge**: A directed connection between two services representing inter-service communication via a specific protocol
- **Conditional_Mode**: A configuration-selected subgraph where certain services and edges appear or disappear based on a config key
- **Service_Container**: A visual grouping element representing a single service with its internal components displayed inside
- **Page_Planner**: The component that decides which diagram pages to generate based on topology type
- **Bidirectional_Edge**: A pair of parallel offset arrows representing communication that flows in both directions between two services
- **Layer_Assignment**: The process of assigning services to vertical layers (client, gateway, service, worker, infrastructure) for grid positioning
- **SERVICE_MAP**: A new page type showing the overall service topology with containers, edges, and conditional groups
- **DEPLOYMENT**: A new page type showing the deployment/infrastructure view of services
- **TopologyType**: An enumeration with values PIPELINE, MICROSERVICE, and HYBRID

## Requirements

### Requirement 1: Topology Classification

**User Story:** As a developer using the drawio-skill, I want the system to automatically detect whether my repository is a pipeline, microservice, or hybrid architecture, so that it generates the appropriate diagram style without manual configuration.

#### Acceptance Criteria

1. WHEN a repository is analyzed, THE Topology_Classifier SHALL return exactly one TopologyType value from the set {PIPELINE, MICROSERVICE, HYBRID} with a confidence score between 0.0 and 1.0
2. WHEN the Topology_Classifier returns PIPELINE, THE Layout_Engine SHALL produce identical output to the pre-feature system with no behavioral changes
3. WHEN the Topology_Classifier cannot determine a topology with high confidence, THE Topology_Classifier SHALL default to PIPELINE with confidence of at least 0.3
4. WHEN at least 3 microservice signals are detected and pipeline score is below 0.3, THE Topology_Classifier SHALL classify the repository as MICROSERVICE
5. WHEN at least 2 pipeline signals are detected with no microservice signals, THE Topology_Classifier SHALL classify the repository as PIPELINE
6. WHEN both pipeline and microservice signals are present with scores at or above 0.3, THE Topology_Classifier SHALL classify the repository as HYBRID

### Requirement 2: Service Discovery

**User Story:** As a developer with a microservice repository, I want the system to identify all services, their ports, protocols, and internal components, so that the diagram accurately represents my system architecture.

#### Acceptance Criteria

1. WHEN a repository is classified as MICROSERVICE or HYBRID, THE Service_Discovery SHALL identify all services by scanning docker-compose files, Kubernetes manifests, Helm charts, Tiltfiles, and service directories
2. WHEN a service is discovered, THE Service_Discovery SHALL extract the service name, path, runtime type, internal components, ports, and dependencies
3. WHEN inter-service communication is detected in source code, THE Service_Discovery SHALL create Communication_Edge records with valid source and target service names from the discovered service set
4. WHEN no docker-compose, Kubernetes manifests, or Tiltfile are found but code shows inter-service communication, THE Service_Discovery SHALL infer services from directory structure and import patterns with reduced confidence

### Requirement 3: Communication Edge Mapping

**User Story:** As a developer, I want the diagram to show all inter-service communication with correct protocol types and directionality, so that I can understand the data flow between services.

#### Acceptance Criteria

1. WHEN scanning service source code, THE Service_Discovery SHALL detect HTTP client calls, gRPC stubs, WebSocket connections, and pub/sub patterns as Communication_Edge instances
2. WHEN edges A-to-B and B-to-A exist with the same protocol, THE Service_Discovery SHALL collapse them into a single Bidirectional_Edge
3. THE Service_Discovery SHALL produce no duplicate edges with the same source, target, and protocol combination
4. WHEN a Communication_Edge only exists under certain configuration values, THE Service_Discovery SHALL annotate it with the conditional mode name

### Requirement 4: Bidirectional Edge Rendering

**User Story:** As a developer viewing the diagram, I want bidirectional communication to be rendered as two visually distinct parallel arrows, so that I can see both directions of data flow clearly.

#### Acceptance Criteria

1. WHEN a Bidirectional_Edge is rendered, THE Layout_Engine SHALL compute two parallel offset paths separated by twice the offset value in pixels
2. WHEN a Bidirectional_Edge is rendered, THE Layout_Engine SHALL ensure the forward and reverse arrow paths do not overlap each other
3. WHEN the source and target nodes are positioned horizontally, THE Layout_Engine SHALL offset the edge paths vertically, and WHEN positioned vertically, THE Layout_Engine SHALL offset the edge paths horizontally

### Requirement 5: Conditional Mode Groups

**User Story:** As a developer with configuration-dependent topology, I want the diagram to show which services and edges belong to each configuration mode, so that I understand how the system behaves under different settings.

#### Acceptance Criteria

1. WHEN a Conditional_Mode is detected, THE Layout_Engine SHALL compute a dashed boundary rectangle that geometrically contains all services belonging to that mode with padding on all sides
2. WHEN a Conditional_Mode group is rendered, THE Layout_Engine SHALL include a label positioned inside the boundary near the top-left corner
3. WHEN computing the Conditional_Mode group boundary, THE Layout_Engine SHALL require at least 2 services in the mode

### Requirement 6: Page Planning by Topology

**User Story:** As a developer, I want the system to generate appropriate diagram pages based on the detected topology, so that the output matches my architecture style.

#### Acceptance Criteria

1. WHEN topology is PIPELINE, THE Page_Planner SHALL generate only OVERVIEW and DRILL_DOWN page types using the existing decomposition rules
2. WHEN topology is MICROSERVICE, THE Page_Planner SHALL generate at least one SERVICE_MAP page
3. WHEN topology is HYBRID, THE Page_Planner SHALL generate at least one OVERVIEW or DRILL_DOWN page and at least one SERVICE_MAP page
4. WHEN a MICROSERVICE topology has conditional modes, THE Page_Planner SHALL generate separate DATA_FLOW pages for each mode showing mode-specific services and edges

### Requirement 7: Service-Map Layout

**User Story:** As a developer, I want services on the service map to be arranged in a clear layered grid without overlapping, so that the diagram is readable and well-organized.

#### Acceptance Criteria

1. WHEN computing the service map layout for N services (1 to 15), THE Layout_Engine SHALL assign non-overlapping bounding boxes to all services
2. WHEN computing the service map layout, THE Layout_Engine SHALL place all service bounding boxes within the page bounds
3. WHEN assigning services to layers, THE Layout_Engine SHALL position client-layer services above gateway-layer services, gateway-layer services above service-layer services, service-layer services above worker-layer services, and worker-layer services above infrastructure-layer services
4. WHEN services are placed within the same layer, THE Layout_Engine SHALL distribute them horizontally with consistent spacing
5. WHEN edges create crossings between layers, THE Layout_Engine SHALL perform within-layer position swaps to reduce the number of edge crossings

### Requirement 8: Layout.py Commands

**User Story:** As a developer extending the skill, I want new layout.py commands for service-map positioning, so that coordinate computation remains deterministic and testable.

#### Acceptance Criteria

1. WHEN the `service-map` command is invoked with a service count N, THE Layout_Engine SHALL output grid positions and page dimensions for a landscape-oriented service map
2. WHEN the `service-container` command is invoked with an internal component count, THE Layout_Engine SHALL output container dimensions and internal component slot positions
3. WHEN the `bidirectional-edge` command is invoked with source and target coordinates, THE Layout_Engine SHALL output forward and reverse edge exit/entry points
4. WHEN the `conditional-group` command is invoked with service positions, THE Layout_Engine SHALL output a bounding box that encloses all specified services with padding

### Requirement 9: Visual Styles

**User Story:** As a developer viewing the diagram, I want distinct visual styles for different element types and protocol-colored edges, so that I can quickly identify service types and communication protocols.

#### Acceptance Criteria

1. WHEN a service container is rendered, THE Layout_Engine SHALL apply a rounded rectangle style with a swimlane header and distinct fill color
2. WHEN an infrastructure node is rendered, THE Layout_Engine SHALL apply a cylinder shape with appropriate fill color
3. WHEN an edge is rendered, THE Layout_Engine SHALL color it according to its protocol: blue for HTTP, purple for gRPC, orange-dashed for WebSocket, and green-dashed for pub/sub
4. WHEN a Conditional_Mode group boundary is rendered, THE Layout_Engine SHALL apply a dashed stroke style with reduced opacity

### Requirement 10: Backward Compatibility

**User Story:** As an existing user of the drawio-skill with pipeline repos, I want no changes to my diagram output, so that the new feature does not introduce regressions.

#### Acceptance Criteria

1. WHEN a repository is classified as PIPELINE, THE Layout_Engine SHALL produce output identical to the pre-feature system
2. THE Layout_Engine SHALL retain all existing commands (swimlanes, inputs, outputs, steps, split, check-approach, nested-container, loop-annotation, n-split, multipage) with unchanged behavior
3. WHEN existing commands are invoked with the same arguments as before the feature, THE Layout_Engine SHALL produce the same output values

### Requirement 11: Error Handling

**User Story:** As a developer, I want the system to handle edge cases gracefully, so that it produces useful output even with unusual repository structures.

#### Acceptance Criteria

1. IF more than 15 services are discovered, THEN THE Service_Discovery SHALL group related services into logical clusters and split across multiple SERVICE_MAP pages
2. IF the edge graph contains cycles, THEN THE Layout_Engine SHALL break cycles at the weakest edge for layout purposes while still rendering all edges in the final diagram
3. IF topology is classified as MICROSERVICE but service discovery finds zero services, THEN THE Topology_Classifier SHALL fall back to PIPELINE classification
4. IF classification confidence is below 0.5 with both pipeline and microservice signals present, THEN THE Topology_Classifier SHALL classify as HYBRID with confidence 0.5

### Requirement 12: Security and Secrets Filtering

**User Story:** As a developer, I want sensitive information to be excluded from diagram labels, so that secrets are not exposed in generated diagrams.

#### Acceptance Criteria

1. WHEN generating service-map labels, THE Layout_Engine SHALL apply the existing secret filtering rules to exclude entries with keys ending in _KEY, _SECRET, _TOKEN, _PASSWORD, or _CREDENTIAL
2. WHEN infrastructure connection strings are found in docker-compose or Kubernetes configs, THE Service_Discovery SHALL strip credentials before including them in node labels
3. WHEN environment variables match secret patterns, THE Service_Discovery SHALL exclude them entirely from node labels
