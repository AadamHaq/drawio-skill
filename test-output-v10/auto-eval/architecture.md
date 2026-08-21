# auto-eval Architecture

## Overview

Environment-driven pipeline for generating and validating synthetic multi-turn conversational datasets. Three-layer architecture: Config drives Pipeline modules, which delegate domain-specific logic to a pluggable Environment.

```mermaid
flowchart TB
    subgraph Config["Config Layer"]
        cfg["generation_plan_ric_v9.yaml<br/>environment: convai_spending_insights<br/>models: deepseek-v4-flash"]
    end

    subgraph Pipeline["Pipeline Layer"]
        gen["Generator<br/>run_generation.py<br/>combo grid → blocks"]
        val["Validator<br/>scorer.py<br/>LLM judge, mean≥8"]
        pp["Post-Processing<br/>assemble → split → rebalance"]
        fixer["Fixer<br/>run_fix.py<br/>LLM rewrite failed turns"]
    end

    subgraph Env["Environment Layer (convai_spending_insights)"]
        tools["ToolSpec Registry<br/>get_tools() → ToolBehavior"]
        exec["ConciergeDBExecutor<br/>PostgreSQL queries"]
        guard["Guardrailing<br/>tag taxonomy + signposting"]
        domval["Domain Validation<br/>validate_tool_call()"]
    end

    cfg --> gen
    cfg --> val
    cfg --> pp

    gen -->|raw blocks| val
    val -->|scored blocks| pp
    val -->|failed| fixer
    fixer -.->|rewrite| gen

    gen -.->|get_tools| tools
    gen -.->|execute_tool| exec
    val -.->|validate| domval
```

## Generator Drill-Down

The generator orchestrates 5 sequential stages per block:

```mermaid
flowchart TB
    subgraph Generator["Generator (run_generation.py → multi_turn_gen.py)"]
        s1["1. Combo Grid<br/>combos.py<br/>dialect × block_type × topic × emotion"]
        s2["2. Query Generation<br/>query model (deepseek-v4-flash, temp=0.7)<br/>generates realistic user message"]
        s3["3. Answer Decision<br/>answer model (temp=0.3, tool_choice=auto)<br/>→ tool_call or NLR response"]
        s4["4. Tool Behavior Dispatch<br/>turn_gen.py<br/>EXECUTE | SYNTHESIZE | DETERMINISTIC | TERMINAL"]
        s5["5. Tool Result + Response<br/>format tool_result<br/>generate narration (≤60 words)"]
    end

    env["Environment<br/>convai_spending_insights<br/>ToolSpec + execute_tool()"]
    db[("PostgreSQL<br/>concierge_eval")]
    output["output/raw/<br/>multi_turn.json"]

    s1 --> s2 --> s3 --> s4 --> s5
    s4 -.->|dispatch| env
    env -.->|SQL| db
    s5 --> output
```

## Data Shapes

| Stage | Format | Key Fields |
|-------|--------|------------|
| Generation output | `output/raw/multi_turn.json` | `messages[]`, `metadata{block_id, persona_id, block_type, topic, emotion}` |
| Validation scored | `output/ann/*_scored.json` | `scores{}`, `pass: bool`, `avg_score: float` |
| Fix input | `output/ann/` (failed blocks) | Same as scored, `pass=false` |
| Assembled | `output/final/multi_turn.json` | Stitched conversations with topic pivots |
| Final split | `output/{train,val,eval}.json` | Ratios from `output:` config section |

## Config Snapshot

| Key | Value | Notes |
|-----|-------|-------|
| `environment` | `convai_spending_insights` | Pluggable domain module |
| `generator.query.model` | `deepseek/deepseek-v4-flash` | OpenRouter remote |
| `generator.answer.model` | `deepseek/deepseek-v4-flash` | temp=0.3, tool_choice=auto |
| `validator.model` | `deepseek/deepseek-v4-flash` | temp=0.1 |
| `validator.threshold` | `8` | Mean score pass gate |
| `validator.hard_fail_threshold` | `5` | Single metric floor |
| `generator.batch_size` | `50` | Concurrent block generation |
| `taxonomy.scenarios[0].pipeline` | `block + assemble` | 2-3 followups per block, 2-3 blocks per convo |
| `guardrailing.enabled` | `true` | Adversarial block pool (corpus mode) |
| `generator.concierge.enabled` | `true` | Real PostgreSQL for EXECUTE tools |

## Pipeline Orchestration

`scripts/run_pipeline.sh` runs the full 4-step pipeline in a tmux session:

1. **STEP 1** — Generation (combo grid → block pool)
2. **STEP 1.5** — Guardrailing adversarial gen (optional, corpus/LLM)
3. **STEP 2** — Annotation (LLM judge scoring, ensemble support)
4. **STEP 3** — Fix (rewrite failed turns, re-annotate)
5. **STEP 4** — Re-annotate fixed samples
6. **Merge + Assemble + Split + Rebalance + Analysis**
