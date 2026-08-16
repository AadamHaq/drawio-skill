# Step 1: Explore the Repository

## What to find

Read entrypoints, orchestrators, configs, and service directories. Answer ALL of:

1. **Inputs** — config files, schemas, data sources, databases
2. **Stages/Services** — scripts, modules, services, pipeline steps (in order if sequential)
3. **Internal sub-steps** — within each stage, what functions are called sequentially?
4. **Decisions** — pass/fail splits, quality gates, routing conditions
5. **Outputs** — files written, APIs served, data produced
6. **Parallel vs sequential** — which stages run side-by-side vs in order?
7. **Concrete details** — exact script paths, model names, temperatures, thresholds, batch sizes, output file paths
8. **Connections** — which input feeds which stage? Which stage's output feeds the next?

## Topology Classification

After exploration, classify the repo:

### Pipeline signals (sequential stage-based)
- Orchestrator script (main.py / run.sh with sequential stage calls)
- Config listing stages in order (YAML with pipeline/stages key)
- Pass/fail quality gates (score thresholds, filtering)
- Output chaining (stage N output = stage N+1 input)
- Single execution flow (runs once to completion)

### Microservice signals (distributed, always-running)
- Docker-compose with multiple services
- Kubernetes manifests (Deployments, Services)
- Multiple service directories (each with own entrypoint)
- Inter-service HTTP/gRPC clients
- WebSocket patterns, message queues
- Helm charts, Tiltfile
- Always-running processes (web servers, event loop workers)

### Decision rules
- ≥3 microservice signals AND pipeline score low → **MICROSERVICE**
- ≥2 pipeline signals AND no microservice signals → **PIPELINE**
- Both present → **HYBRID** (generate both page types)
- Unsure → default to **PIPELINE**

## Output of this step

A mental model of:
- Topology type (PIPELINE / MICROSERVICE / HYBRID)
- List of stages or services with their details
- List of connections between them
- Key config values extracted
