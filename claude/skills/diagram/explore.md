# Step 1: Explore the Repository

## What to find

Read entrypoints, orchestrators, configs, and service directories. Answer ALL of:

1. **Inputs** — config files, schemas, data sources, databases
2. **Modules** — the main code units (packages, services, directories with their own purpose)
3. **Internal sub-steps** — within each module, what functions are called sequentially?
4. **Decisions** — pass/fail splits, quality gates, routing conditions
5. **Outputs** — files written, APIs served, data produced
6. **Concrete details** — exact script paths, model names, temperatures, thresholds, batch sizes, output file paths
7. **Connections** — which module uses which? What calls what?

## Topology Classification

After exploration, answer these questions IN ORDER to determine the topology. Do not match on file names, directory names, or keywords. Reason about the actual architectural relationships.

### Question 1: Are the main modules independently deployable/runnable processes?

- Can each module run as its own long-lived process with its own network endpoint?
- Do they communicate over the network (HTTP, gRPC, WebSocket, message queues)?
- Is there a container/deployment manifest defining how to run them separately?

**If YES to 2+ of these → MICROSERVICE.** Stop here.

### Question 2: Can the main modules run independently of each other?

Pick any two modules you identified. Ask:
- If I deleted module A entirely, would module B still function on its own (given its inputs from somewhere else)?
- Do the modules import from each other's internals, or do they only share a common dependency below them?
- Could someone use module A in a completely different project without bringing module B?

**If YES to all** — the modules are **peers** (they live at the same level, not feeding each other).
**If NO to all** — the modules are **sequential** (one's output is literally the next's input, they form a tight chain with no shared lower layer).
**If MIXED** — some modules feed each other's data, BUT they share a common abstraction/dependency layer below them that each module calls into independently. They are **peers with a data flow** — the execution order exists but it's not what defines the architecture. The shared lower layer is the defining relationship.

Key distinction: "Module A produces data that Module B consumes" does NOT automatically make them sequential. Ask: "Do A and B ALSO both independently call into a shared lower layer?" If yes, the architecture is layered (peers sharing a dependency) with a data pipeline on top (operational ordering). The diagram should show the layers, not just the sequence.

### Question 3: Is there a shared abstraction that multiple modules depend on?

- Is there a base class, protocol, interface, or registry that multiple modules consume?
- Do the modules call into a common lower layer (a domain layer, an execution engine, a shared API)?
- Is there a config that selects/activates which parts of this shared layer are used?

**If YES** — there's a **lower layer** that the modules sit above.

### Question 4: Is there a config/input layer that drives the modules from above?

- Does a single config file determine what modules do (which models, which parameters, which features)?
- Do the modules read from a shared config rather than being hardcoded?
- Could you change the system's behavior entirely by editing config without touching module code?

**If YES** — there's an **upper layer** (config) that the modules sit below.

### Classification Decision

Apply this logic:

```
If Q1 = YES                                              → MICROSERVICE
If Q2 = YES (peers) AND Q3 = YES (lower layer)          → LAYERED
If Q2 = MIXED (data flow + shared lower layer)           → LAYERED (not pipeline!)
If Q2 = NO (tight chain, no shared lower abstraction)    → PIPELINE
If none clearly fit                                      → HYBRID
```

**The critical test for LAYERED vs PIPELINE:**

Ask yourself: "What is the DEFINING architectural relationship in this codebase?"

- If it's "data flows from A → B → C in sequence" and there's no shared abstraction below → **PIPELINE**
- If it's "A, B, C all independently use a shared protocol/layer below them, and config drives everything from above" → **LAYERED** (even if A's output happens to feed B during execution)

A LAYERED system often HAS a data pipeline running through it operationally. But the architecture diagram should show the layers (what depends on what), not just the execution sequence. The execution order can be shown with small flow arrows between peers in the same layer.

### Common traps

- A `run_pipeline.sh` that calls modules in order does NOT automatically mean PIPELINE topology. That's orchestration, not architecture.
- An `environments/` or `plugins/` directory does NOT automatically mean LAYERED. Check if modules actually depend on it.
- Multiple directories with `__init__.py` does NOT mean they're peers. Check if they import from each other in a chain.

## Output of this step

A mental model of:
- Topology type (PIPELINE / MICROSERVICE / LAYERED / HYBRID) with the reasoning for each question
- List of modules with their relationships (peer, sequential, or depends-on)
- The layers if LAYERED/HYBRID: what sits above, what's in the middle, what's below
- Key config values extracted
