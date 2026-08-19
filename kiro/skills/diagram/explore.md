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

**DO NOT conclude the topology until you have written answers to ALL FOUR questions below.** Do not use words like "clearly" or "obviously" — reason through each question with evidence.

### Question 1: Are the main modules independently deployable/runnable processes?

Answer YES or NO with evidence:
- Can each module run as its own long-lived process with its own network endpoint?
- Do they communicate over the network (HTTP, gRPC, WebSocket, message queues)?
- Is there a container/deployment manifest defining how to run them separately?

**If YES to 2+ of these → MICROSERVICE.** Stop here.

### Question 2: Do the main modules share a common abstraction/protocol that they independently consume?

Answer YES or NO with evidence:
- Is there a base class, protocol, interface, or registry that multiple modules call into?
- Do the modules each independently depend on a shared lower layer (not just passing data between each other)?
- Could you swap out that lower layer (different implementation) and the modules would still work unchanged?

Write your answer before moving to Q3.

### Question 3: Can each module function given arbitrary input, without the other modules existing?

Answer YES or NO with evidence for each pair:
- Could the generator work if the validator didn't exist (someone else scores its output)?
- Could the validator work if the generator didn't exist (it just receives data from somewhere)?
- Could post-processing work if both generator and validator didn't exist (given pre-scored data)?
- Do modules import from each other's internals, or only from the shared layer below?

Write your answer before moving to Q4.

### Question 4: Is there a config/input layer that drives all modules from above?

Answer YES or NO with evidence:
- Does a single config file determine what ALL modules do?
- Do the modules read from shared config rather than being hardcoded?
- Could you change system behavior entirely by editing config without changing module code?

### Classification Decision (ONLY after answering all four questions)

Read your answers above and apply:

```
Q1 = YES                                              → MICROSERVICE
Q2 = YES AND Q3 = YES                                 → LAYERED
Q2 = YES AND Q3 = MIXED (modules pass data but also   → LAYERED
    independently consume a shared lower abstraction)     (the shared layer is the defining relationship)
Q2 = NO AND Q3 = NO (tight chain, no shared layer)    → PIPELINE
None clearly fit                                       → HYBRID
```

**The critical test:** Ask yourself: "What would I draw to explain this system to someone new — the sequence of data flow, or the layers of abstraction?" 

- If the first thing you'd explain is "data goes from A to B to C" → PIPELINE
- If the first thing you'd explain is "there are these independent modules, they all plug into this shared protocol/layer, and config wires them together" → LAYERED

A system where modules happen to run sequentially (orchestrated by a script) but architecturally depend on a shared protocol below them is LAYERED, not PIPELINE. The script is operations; the protocol is architecture.

### Common traps

- A `run_pipeline.sh` that calls modules in order is ORCHESTRATION, not architecture. Don't let it bias your classification.
- "Module A's output feeds Module B" does not mean PIPELINE if A and B also independently depend on a shared layer below. That's LAYERED with a data flow on top.
- Multiple directories with Python packages does NOT tell you the topology. Look at what they DEPEND ON, not how they're organized on disk.
- READMEs often describe the execution order ("first generate, then validate, then assemble"). That describes operations, not necessarily architecture. Read the actual imports and abstractions.

## Output of this step

Write out:
1. Your answer to each question (Q1, Q2, Q3, Q4) with specific evidence
2. Your topology classification with reasoning
3. List of modules with their relationships (peer, sequential, or depends-on)
4. The layers if LAYERED/HYBRID: what sits above, what's in the middle, what's below
5. Key config values extracted
