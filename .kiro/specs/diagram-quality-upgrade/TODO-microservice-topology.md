# Follow-Up: Microservice / Non-Pipeline Topology Support

## Context

The current diagram-quality-upgrade spec is designed for **pipeline repos** (sequential stages with pass/fail, like auto-eval). It does not handle microservice architectures well.

## Test Case

Use `~/Code/convai` as the reference repo for this follow-up. It's a distributed system with 7 services (api, realtime, llm, stt, tts, guardrails, web) communicating via HTTP/gRPC/WebSockets/LiveKit.

## Gaps to Address

### 1. Bidirectional / cyclic edges
- Not just loops within a stage, but genuine back-and-forth between components
- Example: voice worker sends audio to TTS and receives audio back; LLM does tool calls back to the API
- Need support for two-way arrows and feedback loops between services

### 2. Service boundary groupings
- Services as containers with internal components, not just "phases"
- Example: the realtime service has text tier, voice tier, pipeline strategies, room manager — all inside one service boundary
- Need a "service container" visual that differs from a swimlane (swimlanes imply sequential steps)

### 3. Conditional topology (config-selected subgraphs)
- Whole subgraphs that appear/disappear based on config
- Example: `pipeline-type=cascade` → STT + vLLM + TTS services exist; `pipeline-type=openai` → only OpenAI Realtime API
- Example: `LLM_CLASSIFIER_ENABLED=true` → classifier path; `false` → legacy Triton cascade
- Need a way to show optional/conditional services with dashed borders or toggle annotations

### 4. Multiple diagram types beyond data flow
- Data flow view: audio frames → STT → LLM → TTS
- Deployment view: Kubernetes pods, LiveKit as SFU, browser as client, network boundaries
- Sequence view: voice escalation flow (already handled by Mermaid companion, but not in draw.io)
- Need distinct PageTypes: SERVICE_MAP, DEPLOYMENT, DATA_FLOW, SEQUENCE

### 5. Always-running vs one-shot nodes
- Pipeline repos have stages that "run and complete"
- Microservice repos have services that are "always running" and respond to events
- Visual distinction needed (e.g., rounded rect for services vs. process boxes for stages)

## Approach Notes

- This should be a separate spec (`microservice-topology-support`)
- It extends the diagram-quality-upgrade work — the multi-page, rich labels, and validation infrastructure all apply
- Key new layout.py commands needed: `service-container`, `bidirectional-edge`, `conditional-group`
- The SKILL.md Step 1 (Explore) needs a topology classifier: "is this a pipeline, a microservice system, or a hybrid?"
- The decomposition planner needs topology-aware page planning
