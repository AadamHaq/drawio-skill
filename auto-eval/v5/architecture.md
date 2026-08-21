# Architecture

## Pipeline Overview

```mermaid
flowchart TD
    subgraph Inputs
        Config["generation_plan_ric_v9.yaml"]
        Personas["persona_banking.jsonl"]
        Context["context_v6.txt"]
        Rubric["annotator_rubric_blocks.yaml"]
    end

    subgraph Generation["Step 1: Block Generation"]
        Gen_Query["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7"]
        Gen_Answer["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3 · tool_choice: auto"]
        Gen_Tool["Tool Result + Response<br/>concierge DB execution<br/>followup_temp: 0.7"]
    end

    subgraph Annotation["Step 2: Annotation"]
        Ann_Dedup["Dedup + Normalise"]
        Ann_Score["Per-Turn LLM Scoring<br/>threshold: 8 · hard_fail: 5"]
        Ann_Filter["Threshold Filter"]
    end

    subgraph Fix["Step 3-4: Fix & Re-Annotate"]
        Fix_Turn["Fix Failed Turns<br/>temp: 0.3 · fix_turn_v2.txt"]
        Fix_Rescore["Re-Annotate Fixed<br/>same thresholds"]
    end

    subgraph PostProc["Step 5: Post-Processing"]
        Post_Assemble["Assemble Blocks<br/>2-3 blocks/conv · join on persona"]
        Post_Split["Split<br/>0% train / 100% eval / 0% val"]
        Post_Rebalance["Rebalance<br/>tool:text ratio control"]
        Post_Analysis["Analysis<br/>balance + coverage report"]
    end

    Inputs --> Generation
    Gen_Query --> Gen_Answer
    Gen_Answer --> Gen_Tool
    Gen_Tool -->|"per turn · repeated 3-4×"| Gen_Query

    Generation -->|"raw/multi_turn.json"| Annotation
    Ann_Dedup --> Ann_Score
    Ann_Score --> Ann_Filter
    Ann_Filter -->|pass| PostProc
    Ann_Filter -->|fail| Fix

    Fix_Turn --> Fix_Rescore
    Fix_Rescore -->|"recovered"| PostProc

    Post_Assemble --> Post_Split
    Post_Split --> Post_Rebalance
    Post_Rebalance --> Post_Analysis

    PostProc --> Eval["output/eval.json"]
    PostProc --> Train["output/train.json"]
    PostProc --> Val["output/val.json"]
```

### Step 1: Block Generation Internals

```mermaid
flowchart TD
    subgraph Gen_Internal["Block Generation Pipeline"]
        Gen_Combo["Combo Grid Build<br/>dialect × block_type × topic<br/>× emotion × typing_style<br/>batch: 50 · samples_per_combo: 1"]
        Gen_QGen["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7 · max_tokens: 8192<br/>persona + emotion + topic → query"]
        Gen_AGen["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3 · tool_choice: auto<br/>tools: visualise_data + capture_response<br/>+ tag_guardrail_topics"]
        Gen_TRes["Tool Result + Assistant Response<br/>concierge DB real execution<br/>tool_call_correction: enabled<br/>correction temp: 0.1"]
        Gen_Write["Write Block<br/>→ output/raw/multi_turn.jsonl"]
    end

    Gen_Combo --> Gen_QGen
    Gen_QGen --> Gen_AGen
    Gen_AGen --> Gen_TRes
    Gen_TRes -->|"per turn · repeated 3-4×"| Gen_QGen
    Gen_TRes --> Gen_Write
```

### Step 2-4: Annotation & Fix Internals

```mermaid
flowchart TD
    subgraph Ann_Internal["Annotation Pipeline"]
        Ann_Dedup2["Deduplication<br/>tier-1: identical query sequences<br/>remove truncated · normalise"]
        Ann_Schema["Schema Validation<br/>tool name · category check<br/>compare_with rules"]
        Ann_LLM["Per-Turn LLM Scoring<br/>model: deepseek-v4-flash<br/>temp: 0.1 · 6-7 core dims<br/>+ 5 tone insight dims"]
        Ann_Thresh["Threshold Filter<br/>avg ≥ 8, no dim ≤ 5<br/>insight: mean ≥ 5, no dim ≤ 2"]
    end

    subgraph Fix_Internal["Fix & Re-Annotate"]
        Fix_Fix["Fix Failed Turn<br/>model: deepseek-v4-flash<br/>fix_turn_v2.txt · type-flip"]
        Fix_ReAnn["Re-Annotate<br/>same model + thresholds<br/>ensemble: min avg per turn"]
        Fix_Merge["Merge<br/>pass(step2) + pass(step4)<br/>→ final/multi_turn.json"]
    end

    Ann_Dedup2 --> Ann_Schema
    Ann_Schema --> Ann_LLM
    Ann_LLM --> Ann_Thresh
    Ann_Thresh -->|pass| Fix_Merge
    Ann_Thresh -->|fail| Fix_Fix
    Fix_Fix --> Fix_ReAnn
    Fix_ReAnn -->|pass| Fix_Merge
    Fix_ReAnn -->|fail| Discarded["Discarded"]
```

### Step 5: Post-Processing Internals

```mermaid
flowchart TD
    subgraph Post_Internal["Post-Processing Pipeline"]
        Post_Asm["Assemble Blocks<br/>2-3 blocks/conversation<br/>join: persona_id + dialect + date<br/>transition_weights: tool/nlr/guard<br/>forbid_same_type_run: 2"]
        Post_Spl["Split<br/>ratio: 0% train / 100% eval / 0% val<br/>shuffle seed: 42<br/>distillation vs benchmark format"]
        Post_Reb["Rebalance<br/>filter broken exercises<br/>tool:text ratio adjustment<br/>per-category contamination control"]
        Post_Ana["Analysis<br/>dataset balance · enum distributions<br/>category coverage<br/>keyword contamination by category"]
    end

    Guard["guardrailing_blocks.json"] --> Post_Asm
    Final["final/multi_turn.json"] --> Post_Asm
    Post_Asm --> Post_Spl
    Post_Spl --> Post_Reb
    Post_Reb --> Post_Ana
    Post_Ana --> Eval["output/eval.json"]
    Post_Ana --> Train["output/train.json"]
    Post_Ana --> Val["output/val.json"]
```

## Data Shapes

| Stage | Input | Output |
|---|---|---|
| Block Generation | config.yaml, personas.jsonl, context_v6.txt, Concierge DB | output/raw/multi_turn.json |
| Guardrailing Gen | config.yaml, fewshot corpus | guardrailing_raw/guardrailing_blocks.json |
| Annotation | raw/multi_turn.json | final/multi_turn.json + multi_turn_scored.json |
| Fix | *_scored.json (failed only) | fixed/multi_turn.json + fixed/passing/*.json |
| Re-Annotate | fixed/multi_turn.json | rescored/multi_turn.json |
| Assemble | final/multi_turn.json + guardrailing_blocks.json | final/multi_turn.json (overwritten) |
| Split | final/multi_turn.json | eval.json, train.json, val.json |
| Rebalance | train.json | train.json (overwritten) |
| Analysis | train.json | report.md (printed) |

## Config Snapshot

| Parameter | Value |
|---|---|
| query model | deepseek/deepseek-v4-flash |
| answer model | deepseek/deepseek-v4-flash |
| annotator model | deepseek/deepseek-v4-flash |
| fixer model | deepseek/deepseek-v4-flash |
| query temperature | 0.7 |
| answer temperature | 0.3 |
| followup temperature | 0.7 |
| annotator temperature | 0.1 |
| fixer temperature | 0.3 |
| max_tokens | 8192 |
| annotation threshold | 8 |
| hard_fail_threshold | 5 |
| insight_threshold | 5 |
| insight_hard_fail_floor | 2 |
| batch_size | 50 |
| samples_per_combo | 1 |
| followups per block | 2-3 |
| blocks_per_conversation | 2-3 |
| type_ratio | tool: 0.5 / nlr: 0.5 |
| distillation_ratio | 0.0 |
| eval_ratio | 1.0 |
| validation_ratio | 0.0 |
| concierge DB | enabled (PostgreSQL) |
| capture_response | enabled |
| guardrail_in_generation | enabled |
| tool_call_correction | enabled |
| simulation_date_range | 2026-01-01 to 2026-12-31 |
