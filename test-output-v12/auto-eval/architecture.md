# auto-eval Architecture

> Open [architecture.drawio](architecture.drawio) in draw.io for the editable diagram.
> SVGs: [Page 1 (Overview)](architecture_p1.svg) · [Page 2 (Generator)](architecture_p2.svg)

## Overview (Pipeline)

```mermaid
flowchart TD
    subgraph Inputs
        CFG["Config YAML<br/>generation_plan_ric_v9.yaml"]
        ENV["Environment Module<br/>convai_spending_insights"]
    end

    subgraph Generator ["Generator (Step 1)"]
        G1["Combo Grid Builder<br/>combos.py"]
        G2["Block Generation Loop<br/>multi_turn_gen.py"]
        G1 --> G2
    end

    subgraph Validator ["Validator (Step 2)"]
        V1["LLM Scorer<br/>scorer.py · deepseek-v4-flash"]
        V2["Pass/Fail Gate<br/>mean≥8, hard_fail≤5"]
        V1 --> V2
    end

    subgraph PostProcessing ["Post-Processing (Step 4)"]
        P1["Assemble Blocks<br/>assemble_blocks.py"]
        P2["Split + Rebalance<br/>split.py · rebalance.py"]
        P1 --> P2
    end

    FIX["Fix Failed Turns (Step 3)<br/>fixer.py · LLM rewrite"]

    CFG --> Generator
    CFG --> Validator
    ENV --> Generator
    Generator -->|raw blocks| Validator
    V2 -->|failed| FIX
    FIX -->|re-score| Validator
    V2 -->|passing| PostProcessing
    PostProcessing -->|eval.json| OUT["output/eval.json"]
```

## Generator Drill-Down

```mermaid
flowchart LR
    subgraph Generator ["Generator Swimlane"]
        direction TB
        S1["Load Config + Init Env<br/>config.py · registry"]
        S2["Query Generation<br/>generate_queries_block.txt<br/>temp=0.7"]
        S3["Answer Decision<br/>answer_gen.py<br/>tool_choice=auto · temp=0.3"]
        S4["Tool Result<br/>turn_gen.py<br/>ToolBehavior dispatch"]
        S5["Tool Call Correction<br/>correction.py<br/>temp=0.1 · optional"]
        S1 --> S2 --> S3 --> S4 --> S5
    end

    CFG["Config YAML"]
    LLM["LLM (OpenRouter)<br/>deepseek-v4-flash"]
    ENVMOD["Environment<br/>convai_spending_insights"]
    PG[("PostgreSQL<br/>concierge_eval")]

    S1 -->|load YAML| CFG
    S2 -->|query model| LLM
    S3 -->|answer model| LLM
    S4 -->|execute_tool| ENVMOD
    ENVMOD -->|SQL query| PG
    S5 -.->|correction| LLM
```

## Data Shapes

| Stage | Input | Output | Format |
|-------|-------|--------|--------|
| Combo Grid | Config YAML | Combo list | `[{dialect, type, topic, emotion, typing_style}]` |
| Block Generation | Combo + Context | Block pool | `{"messages": [...], "metadata": {...}}` |
| Validation | Raw blocks | Scored blocks | Block + per-turn scores (mean, pass/fail) |
| Fix | Failed turns | Rewritten turns | Same block format, re-scored |
| Assemble | Passing blocks | Conversations | Multi-block stitched with topic pivots |
| Split | Conversations | train/val/eval | Configurable ratios (default: 100% eval) |

## Config Snapshot

| Key | Value | Notes |
|-----|-------|-------|
| `environment` | `convai_spending_insights` | Pluggable domain module |
| `generator.query.model` | `deepseek/deepseek-v4-flash` | Via OpenRouter |
| `generator.answer.model` | `deepseek/deepseek-v4-flash` | Via OpenRouter |
| `generator.batch_size` | `50` | Concurrent blocks |
| `validator.model` | `deepseek/deepseek-v4-flash` | Rubric-driven scorer |
| `validator.threshold` | `8` | Mean score gate |
| `validator.hard_fail_threshold` | `5` | Per-metric floor |
| `fixer.model` | `deepseek/deepseek-v4-flash` | Rewrite failed turns |
| `taxonomy.scenarios[0].pipeline[0].followups` | `{min: 2, max: 3}` | Follow-ups per block |
| `taxonomy.scenarios[0].pipeline[1].blocks_per_conversation` | `{min: 2, max: 3}` | Assembly target |
| `concierge.database_url` | `postgresql+asyncpg://...localhost:5432/concierge_eval` | EXECUTE mode |
| `guardrailing.enabled` | `true` | Adversarial block pool |
| `guardrailing.query_source` | `corpus` | Pre-labelled queries |
