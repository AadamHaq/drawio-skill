# Architecture

## Pipeline Overview

```mermaid
flowchart TD
    subgraph Inputs
        Config["generation_plan.yaml<br/>config-driven pipeline settings"]
        Persona["persona_banking.jsonl<br/>UK banking personas"]
        Rubric["annotator_rubric_blocks.yaml<br/>per-turn-type scoring rubrics"]
    end

    subgraph Generation["Step 1: Generation (Block Stage)"]
        Gen_Blocks["Block Generation<br/>deepseek-v4-flash · query + answer"]
    end

    subgraph Guardrailing["Step 1.5: Guardrailing"]
        Guard_Gen["Adversarial Block Pool<br/>corpus mode · 200 samples"]
    end

    subgraph Annotation["Step 2: Annotation"]
        Ann_Score["LLM Scoring<br/>threshold 8 · hard_fail 5"]
    end

    subgraph Fix["Step 3: Fix"]
        Fix_Turns["Fix Failed Samples<br/>deepseek-v4-flash · rewrite turns"]
    end

    subgraph ReAnnotation["Step 4: Re-Annotation"]
        ReAnn_Score["Re-Score Fixed<br/>merge with originally passing"]
    end

    subgraph PostProcessing["Step 5: Post-Processing"]
        Post_Assemble["Assemble + Split + Rebalance"]
    end

    subgraph Outputs
        Eval["eval.json"]
        Train["train.json"]
        Val["val.json"]
    end

    Inputs --> Generation
    Inputs --> Guardrailing
    Generation --> Annotation
    Guardrailing --> Annotation
    Rubric --> Annotation
    Annotation -->|"pass"| ReAnnotation
    Annotation -->|"fail"| Fix
    Fix --> ReAnnotation
    ReAnnotation --> PostProcessing
    PostProcessing --> Eval
    PostProcessing --> Train
    PostProcessing --> Val
```

---

### Step 1: Generation Internals

```mermaid
flowchart TD
    subgraph Gen_Internal["Block Generation Pipeline"]
        Gen_Combos["Build Combos<br/>dialect × type × topic × emotion × style"]
        Gen_Query["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7"]
        Gen_Answer["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3 · followup: 0.7"]
        Gen_Tool["Tool Result + Response<br/>concierge DB · tool_choice=auto"]
    end

    Gen_Combos --> Gen_Query
    Gen_Query --> Gen_Answer
    Gen_Answer --> Gen_Tool
    Gen_Tool -->|"repeated 2-3×"| Gen_Query
    Gen_Tool -->|"pass"| Block_Pass["Block Pass"]
    Gen_Tool -->|"fail"| Block_Retry["Retry / Drop"]
```

---

### Step 2: Annotation Internals

```mermaid
flowchart TD
    subgraph Ann_Internal["Annotation Pipeline"]
        Ann_Dedup["Deduplication<br/>normalise + remove truncated"]
        Ann_Schema["Schema Validation<br/>tool calls · category names · params"]
        Ann_Scoring["LLM Scoring (per turn)<br/>model: deepseek-v4-flash · temp: 0.1<br/>metrics by turn type"]
    end

    Ann_Dedup --> Ann_Schema
    Ann_Schema --> Ann_Scoring
    Ann_Scoring -->|"avg ≥ 8"| Ann_Pass["Pass"]
    Ann_Scoring -->|"avg < 8 or hard_fail"| Ann_Fail["Fail → Fix Stage"]
```

---

### Step 5: Post-Processing Internals

```mermaid
flowchart TD
    subgraph Post_Internal["Post-Processing Pipeline"]
        Post_Assemble["Assemble Blocks<br/>2-3 blocks/conv · transition weights"]
        Post_Split["Split<br/>eval: 100% (configurable ratios)"]
        Post_Rebalance["Rebalance<br/>tool:text ratio · contamination control"]
        Post_Analysis["Analysis<br/>balance · coverage · contamination report"]
    end

    Post_Assemble --> Post_Split
    Post_Split --> Post_Rebalance
    Post_Rebalance --> Post_Analysis
    Post_Analysis --> Out_Eval["eval.json"]
    Post_Analysis --> Out_Train["train.json"]
    Post_Analysis --> Out_Val["val.json"]
```

---

## Data Shapes

| Stage | Input | Output |
|---|---|---|
| Generation | config YAML, personas JSONL, context prompt | `output/raw/multi_turn.json` (block pool) |
| Guardrailing | config YAML, corpus/LLM | `guardrailing_raw/guardrailing_blocks.json` |
| Annotation | raw blocks, rubric YAML | `output/final/multi_turn.json` (passing), `*_scored.json` (all) |
| Fix | scored failing samples | `output/fixed/multi_turn.json` (rewritten) |
| Re-Annotation | fixed samples | `output/rescored/multi_turn.json` |
| Post-Processing | final blocks + guardrailing pool | `eval.json`, `train.json`, `val.json` |

### Block Schema (per sample)

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "tool_calls": [...]},
    {"role": "tool", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "block_id": "uuid",
    "persona_id": "string",
    "persona": "description",
    "dialect": "Standard British English",
    "block_type": "tool|nlr",
    "emotion": "neutral",
    "typing_style": "casual",
    "topic": "trends|comparisons|...",
    "date": "2026-MM-DD"
  }
}
```

### Scored Sample (annotation output)

```json
{
  "messages": [...],
  "metadata": {...},
  "scores": {
    "pass": true,
    "turns": [
      {
        "turn_index": 0,
        "position": "opening",
        "kind": "tool",
        "metrics": {"naturalness": 9, "when2call": 10, ...},
        "avg": 9.2
      }
    ]
  }
}
```

---

## Config Snapshot

| Parameter | Value |
|---|---|
| query model | deepseek/deepseek-v4-flash |
| answer model | deepseek/deepseek-v4-flash |
| query temp | 0.7 |
| answer temp | 0.3 |
| followup temp | 0.7 |
| annotator model | deepseek/deepseek-v4-flash |
| annotator temp | 0.1 |
| threshold | 8 |
| hard_fail_threshold | 5 |
| insight_threshold | 5 |
| fixer model | deepseek/deepseek-v4-flash |
| fixer temp | 0.3 |
| max_retries | 3 |
| batch_size | 50 |
| blocks_per_conversation | 2-3 |
| followups per block | 2-3 |
| type_ratio | tool: 0.5, nlr: 0.5 |
| eval_ratio | 1.0 |
| guardrailing | enabled (corpus mode, 200 samples) |
| concierge DB | enabled (PostgreSQL) |
