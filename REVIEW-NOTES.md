# Diagram Quality Review — v13 Test Output

## Layout & Rendering Issues (Fix in render_svg.py / layout.py / render guides)

### P1 — Must Fix

| # | Diagram | Issue | Root Cause | Fix |
|---|---------|-------|-----------|-----|
| 1 | auto-eval | **Config→Val crosses Pipeline header** | e-cfg-val has no waypoints, straight (415,100)→(413,214). Z-order header covers it but edge appears to "start from behind header" | Skill should always produce waypoints for cross-band edges. Add to layered/render.md: "Cross-layer edges MUST have at least one waypoint in the gap between bands" |
| 2 | auto-eval | **Gen-Val gap only 35px** (rule says 80px for labeled edges) | Layout computed items at x=48,w=220 and x=303,w=220. Gap = 303-268 = 35px | The `layers` command or skill guidance needs to enforce min 50px gap when items are side-by-side. Or reduce item widths. |
| 3 | convai p2 | **df-step5 and df-step6 OVERLAP by 20px** | step5 at y=301,h=44 (bottom=345), step6 at y=325. Hard rendering bug. | Agent didn't use `layout.py steps` to compute positions. Should be enforced in skill: "ALWAYS compute step positions with layout.py steps, never place manually" |
| 4 | auto-eval | **Sequential step edges are 14px (barely visible)** | Step gap = step[n+1].y - step[n].y - step[n].h = 310-296 = 14px. Skill constant _STEP_GAP=30 wasn't used. | Same as #3 — steps were manually placed, not computed |

### P2 — Should Fix

| # | Diagram | Issue | Fix |
|---|---------|-------|-----|
| 5 | convai-lab | **e-ceval-view routes at y=240** (12px below header, above items) | Edge should route below the items (y=310+) or the gap should be larger. Add validation: "no horizontal waypoint should be within 20px of a band header bottom" |
| 6 | auto-eval | **"execute" label truncated** from "execute_tool()" | The edge label in the drawio is "execute" but the original function is `execute_tool()`. The skill's 12-char label rule is too aggressive for this use case. Should preserve the function name. |
| 7 | all layered | **validate.py reports 19-23 false positives** | All BOX CROSSING warnings for background bands. validate.py needs a `--layered` flag or auto-detection that suppresses crossings through swimlane-typed nodes that are background bands (not source/target of the edge) |
| 8 | convai | **Duplicate "completions" label** on two different edges (e5 and e7) | Confusing — reader can't tell which is RT-Text→LLM vs RT-Voice→LLM. One should say "chat comp" and the other "voice comp" or similar |

### P3 — Nice to Have

| # | Diagram | Issue |
|---|---------|-------|
| 9 | auto-eval | Gen height 400 vs needed 358 (42px dead space) — within tolerance but visible |
| 10 | convai-lab | Only 1 page for a repo with 4 runners + 3 environment components. No drill-down. |
| 11 | auto-eval | No drill-down page despite Generator having 5 sub-steps |

---

## Content / Information Quality Issues

### Auto-eval — GOOD but gaps:

**What's well captured:**
- Generator sub-steps are detailed: Combo Grid, Query Gen, Answer Decision, ToolBehavior Dispatch, Correction — all with parameters
- Validator flow: LLM Scorer → Pass/Fail Gate → Fix + Re-score → Dedup
- Environment items: Tool Execution, Validation Rules, Prompts, Tool Schema, Persona DB, DomainConfig — covers the key components
- Config mentions `generation_plan_*.yaml` with key fields (environment, models, taxonomy, thresholds)

**Missing / too thin:**
1. **No mention of specific models** — The config shows `minimax/minimax-m3`, `z-ai/glm-5.2`, OpenRouter endpoints, vLLM local. These are concrete details that make the diagram useful. Should appear in Generator or Config.
2. **No mention of "multi-ann ensemble"** — v10's key feature is dual-model annotation with min-average scoring. This is architecturally significant.
3. **No mention of guardrailing** — The config has a whole `guardrailing:` section with adversarial block generation. Not captured.
4. **"Correction (LLM rewrite on fail)"** — imprecise. It's specifically the Fix + Re-annotate loop, not a generic correction.
5. **Post-Processing "Analysis (quality report)"** — vague. Should mention what's in the report (score distributions, per-dimension breakdowns, pass rates).
6. **Missing: scripts/run_pipeline.sh** — The orchestrator script with its numbered steps (STEP 1: gen, STEP 1.5: guardrailing, STEP 2: annotate, etc.) is architecturally important but not shown.
7. **"Dedup + Filter" in Validator** — actually this is in post-processing, not validation. The validator produces scores; dedup happens after.
8. **Missing: batch size / parallelism** — Config specifies batch_size=20, num_workers, retry logic. These are operational details but useful.
9. **Missing: output paths** — Where data lands (output/run_X/, artifacts/) is useful for understanding the flow.

### Convai-lab — TOO THIN:

**What's there:**
- Config items: eval_params.py, prompt_arms/, datasets/ — correct
- Runners: sweep.py, run_ceval.py, prompt_runner.py, view/ — correct
- Environment: registry.py, environments/e0-e15, convai/ submodule — correct

**Missing:**
1. **No sub-labels with meaningful content** — "sweep.py / matrix driver" tells you nothing. Should say: "sweep.py: iterates (model × prompt_arm × dataset) matrix, launches run_ceval per cell"
2. **No mention of what eval_params.py contains** — It defines named evaluation configurations (which models, which arms, which scenarios to cross). Should list example params.
3. **"environments/e0-e15 / frozen tool snapshots"** — What's frozen? The tool schemas, the prompts, the DB state? Should say "frozen ToolSpec+prompts+db-seed per arm"
4. **"convai/ submodule / pinned product SHA"** — Good but what does the submodule provide? Should say "provides runtime (API + realtime services) for live-mode evaluation"
5. **No mention of results/** — Where outputs land, what format (JSON scores, per-cell reports)
6. **view/ says "inspector + webapp"** — Should mention what you can inspect (per-turn scores, prompt diffs, side-by-side comparison)
7. **Missing: the ceval execution model** — Each cell spawns a subprocess with `uv run --frozen`, writes to results/{eval_name}/{cell_id}/. This is architecturally significant.
8. **Missing: persona_db/** — Listed in the repo but not on the diagram. Contains persona banking data for evaluation scenarios.

### Convai — GOOD:

**Service Map well captured:**
- All 7+ services with correct ports and tech (FastAPI, Triton, vLLM, LiveKit)
- LMCache noted alongside vLLM — good architectural detail
- Banking (BoA) domain noted in API — specific
- WebSocket vs WebRTC vs gRPC vs HTTP protocol distinctions — all correct

**Voice Pipeline data flow — good:**
- 6-step sequential flow inside the worker is correct
- External dependencies (STT, LLM, Guardrails, TTS) positioned correctly
- Protocol labels on cross-service edges are accurate

**Missing:**
1. **No mention of mode switching** — convai supports text mode and voice mode with different code paths. Only voice is shown on page 2.
2. **No mention of the cascade/openai model selection** — The LLM service can use different backends depending on config.
3. **API "Banking (BoA)"** — Should mention what banking features (account summaries, spending categories, transaction search). Currently too abstract.
4. **Missing: configuration/helm** — How services are deployed (docker-compose locally, K8s in prod) is useful context.
5. **No Redis KV-Cache connection shown** — redis-kv is defined but no edge connects to it. It's used by vLLM/LMCache. Should have a dashed edge from LLM → Redis KV.

---

## Plan: Priority Fixes

### Immediate (skill rules & validation):

1. **Add to layered/render.md**: "Cross-layer edges MUST include at least one waypoint at y = gap_midpoint between source band bottom and target band top"
2. **Add to layered/render.md**: "Minimum 50px horizontal gap between sibling items. If items won't fit with 50px gaps, reduce item width."
3. **Add to SKILL.md Step 3**: "NEVER manually place steps inside swimlanes. ALWAYS use `layout.py steps` to compute y-positions. Manual placement causes overlap and invisible arrows."
4. **Update validate.py**: Add `--topology layered` flag that suppresses BOX CROSSING warnings for swimlane-typed background bands.
5. **Update edge-rules.md**: "Max edge label is 12 chars UNLESS it's a function/method name — preserve those as-is up to 20 chars."

### Medium term (content quality):

6. **Add to explore.md output section**: "For each module, include: specific model names, key thresholds, output locations, batch sizes — not just the module name."
7. **Add richness guidance to layered/render.md**: "Sub-labels should explain WHAT the component does, not just its filename. Bad: 'sweep.py / matrix driver'. Good: 'sweep.py / iterates model×arm×dataset matrix, launches cells'"
8. **Add to SKILL.md Step 2**: "For LAYERED repos, check if any module has 3+ sub-steps that warrant a drill-down page."

### Later (renderer improvements):

9. Fix step overlap detection in validate.py (check child geometries don't overlap within same parent)
10. Reduce duplicate labels (validate.py should flag same label text on different edges)
11. Consider auto-detecting "too thin" content — if a box has only 2 words of description, flag it
