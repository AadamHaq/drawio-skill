# Synthetic Banking Dataset Pipeline — Architecture

## Overview

```mermaid
flowchart TD
    subgraph Inputs
        CFG[generation_plan_ric_v9.yaml<br/>domain · models · taxonomy]
        RUB[annotator_rubric_blocks.yaml<br/>metrics · hard-fail rules]
        PER[persona_banking.jsonl<br/>UK banking personas]
    end

    subgraph "1. Block Generation"
        QG[Query Generation<br/>deepseek-v4-flash · temp 0.7]
        AG[Answer Generation<br/>tool_choice=auto · temp 0.3]
        TR[Tool Result + Response<br/>synthesise result → reply]
    end

    subgraph "2. Annotation"
        DD[Dedup + Schema Validate]
        SC[Score Each Turn<br/>threshold ≥ 8 · hard_fail ≤ 5]
        PA[Pass]
        FA[Fail]
    end

    subgraph "3. Fix"
        FX[Rewrite Failing Turns<br/>reground tool calls via Concierge]
    end

    subgraph "4. Re-Annotate"
        RA[Re-score Fixed Samples<br/>merge with originally passing]
    end

    subgraph "5. Post-Processing"
        ASM[Assemble Blocks<br/>2-3 blocks/conv · transition weights]
        SPL[Split<br/>train / eval / val ratios]
        REB[Rebalance<br/>tool:text ratio · category balance]
        ANL[Analysis<br/>coverage · contamination report]
    end

    subgraph Outputs
        TRN[train.json<br/>distillation format]
        EVL[eval.json<br/>benchmark format]
        VAL[val.json<br/>distillation format]
    end

    CFG --> QG
    PER --> QG
    QG --> AG --> TR
    TR -->|raw blocks| DD
    RUB --> SC
    DD --> SC
    SC -->|≥ 8| PA
    SC -->|< 8| FA
    FA -->|failed| FX
    FX -->|fixed| RA
    PA -->|passed| ASM
    RA -->|re-scored| ASM
    ASM --> SPL --> REB --> ANL
    SPL --> TRN
    SPL --> EVL
    SPL --> VAL
```

## Block Generation Detail

```mermaid
flowchart TD
    subgraph Inputs
        TX[taxonomy<br/>tool_topics · nlr_topics<br/>emotions · typing_styles · dialects]
        TS[tool_schema.json<br/>visualise_data · capture_response<br/>tag_guardrail_topics]
        PS[personas<br/>JSONL pool or persona-DB<br/>Postgres reseed per persona]
    end

    subgraph "Block Generation (per combo)"
        CG[Build Combo Grid<br/>dialect × type × topic × emotion × style<br/>samples_per_combo: 1]
        S1[Stage 1: Query Generation<br/>prompt: generate_queries_block.txt<br/>context + persona + metadata → user msg]
        S2[Stage 2: Answer Generation<br/>tools=schema, tool_choice=auto<br/>model decides: tool / NLR / capture_response]
        S3[Stage 3: Tool Result + Response<br/>synthesise tool result<br/>generate assistant reply · retry on fail]
        FU[Follow-ups 2-3×<br/>repeat S1→S2→S3 with history<br/>same topic · followup_temp: 0.7]
        BK[Output: block dict<br/>messages + metadata]
    end

    subgraph Assembly
        GR[Group by join_keys<br/>persona_id + dialect + date]
        PK[Pick Backbone Sequence<br/>transition_weights · forbid_same_type_run: 2]
        ST[Stitch + Guardrailing<br/>least-used-first · topic dedup<br/>guardrailing blocks via probability]
    end

    OUT[multi_turn.json<br/>full conversations: 2-3 blocks stitched]

    TX --> CG
    TS --> S2
    PS --> CG
    CG --> S1 --> S2 --> S3 --> FU --> BK
    BK -->|block pool| GR --> PK --> ST --> OUT
```

## Data Shapes

| Stage | Input | Output | Format |
|-------|-------|--------|--------|
| Generation | combo grid (taxonomy × personas) | `raw/multi_turn.json` | `[{messages, metadata}]` per block |
| Annotation | raw blocks | `ann/multi_turn.json` (passed) + `*_scored.json` | blocks with `scores.pass` bool |
| Fix | `*_scored.json` (failed) | `fixed/multi_turn.json` | rewritten blocks (scores stripped) |
| Re-annotate | fixed blocks | `rescored/multi_turn.json` | re-scored blocks |
| Merge | passed + re-scored | `final/multi_turn.json` | combined passing blocks |
| Assemble | final blocks | `final/multi_turn.json` (overwritten) | full conversations (multi-block) |
| Split | assembled conversations | `train.json` / `eval.json` / `val.json` | distillation or benchmark format |
| Rebalance | `train.json` | `train.json` (overwritten) | filtered + balanced |
| Analysis | `train.json` | report (stdout) | coverage + contamination stats |

## Config Snapshot

| Key | Value | Source |
|-----|-------|--------|
| Generator model | `deepseek/deepseek-v4-flash` | `generator.answer.model` |
| Query temperature | 0.7 | `generator.query.temperature` |
| Answer temperature | 0.3 | `generator.answer.temperature` |
| Followup temperature | 0.7 | `generator.answer.followup_temperature` |
| Annotator model | `deepseek/deepseek-v4-flash` | `annotator.model` |
| Pass threshold | ≥ 8 (avg) | `annotator.threshold` |
| Hard-fail floor | ≤ 5 | `annotator.hard_fail_threshold` |
| Insight threshold | ≥ 5 | `annotator.insight_threshold` |
| Blocks per conversation | 2-3 | `taxonomy.scenarios[0].pipeline[1].blocks_per_conversation` |
| Join keys | persona_id, dialect, date | `taxonomy.scenarios[0].pipeline[1].join_keys` |
| Type ratio | tool 0.5 / nlr 0.5 | `taxonomy.scenarios[0].pipeline[0].type_ratio` |
| Followups per block | 2-3 | `taxonomy.scenarios[0].pipeline[0].followups` |
| Output split | 0% train / 100% eval / 0% val | `output.distillation_ratio` / `eval_ratio` |
| Orchestrator | `scripts/run_pipeline.sh` | tmux session: pipeline / vllm / gpu |
