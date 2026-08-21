# Architecture

## Pipeline Overview

```mermaid
flowchart TD
    subgraph Inputs
        Config["generation_plan_ric_v9.yaml"]
        Personas["persona_banking.jsonl"]
        Context["context_v6.txt"]
    end

    subgraph Generation["Step 1: Block Generation"]
        Gen_Query["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7"]
        Gen_Answer["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3"]
        Gen_Tool["Tool Result + Response<br/>followups: 2-3 per block"]
    end

    subgraph Guardrailing["Step 1.5: Guardrailing"]
        Guard_Gen["Generate Adversarial Queries<br/>corpus mode · 200 samples"]
        Guard_Verify["Verify with Guard Tool<br/>signpost response injection"]
    end

    subgraph Annotation["Step 2: Annotation"]
        Ann_Dedup["Dedup + Truncation Filter"]
        Ann_Schema["Schema Validation"]
        Ann_Score["Per-Turn LLM Scoring<br/>threshold: 8 · hard_fail: 5"]
    end

    subgraph PostProcessing["Step 5: Post-Processing"]
        Post_Assemble["Assemble Blocks<br/>2-3 blocks per conversation"]
        Post_Split["Split<br/>100% eval (ric_v9)"]
        Post_Rebalance["Rebalance<br/>tool:text ratio"]
        Post_Analysis["Analysis<br/>balance + coverage report"]
    end

    Config --> Generation
    Personas --> Generation
    Context --> Generation
    Config --> Guardrailing

    Gen_Query --> Gen_Answer
    Gen_Answer --> Gen_Tool
    Gen_Tool -->|"repeated 2-3×"| Gen_Query

    Guard_Gen --> Guard_Verify

    Generation --> Annotation
    Ann_Dedup --> Ann_Schema
    Ann_Schema --> Ann_Score
    Ann_Score -->|"avg ≥ 8"| Pass_Ann["Pass"]
    Ann_Score -->|"avg < 8"| Fail_Ann["Fail"]

    Fail_Ann --> Fix["Fix Failed Samples<br/>model: deepseek-v4-flash"]
    Fix --> ReAnn["Re-Annotation<br/>same scoring pipeline"]
    ReAnn --> PostProcessing
    Pass_Ann --> PostProcessing
    Guardrailing --> PostProcessing

    Post_Assemble --> Post_Split
    Post_Split --> Post_Rebalance
    Post_Rebalance --> Post_Analysis

    PostProcessing --> Eval_Out["output/eval.json"]
    PostProcessing --> Train_Out["output/train.json"]
```

---

### Step 1: Block Generation Internals

```mermaid
flowchart TD
    subgraph Gen_Internal["Block Generation Pipeline"]
        Gen_Prompt["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7 · max_tokens: 8192<br/>📄 generator/run_generation.py"]
        Gen_LLM["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3 · tool_choice: auto<br/>📄 generator/answer_gen.py"]
        Gen_ToolRes["Tool Result Generation<br/>synthesise result + response<br/>📄 generator/turn_gen.py"]
        Gen_Followup["Follow-up Turn<br/>followup_temp: 0.7<br/>same topic, no pivot<br/>📄 generator/multi_turn_gen.py"]
    end

    Config_In["generation_plan_ric_v9.yaml"] --> Gen_Internal
    Persona_In["persona_banking.jsonl"] --> Gen_Internal
    Context_In["context_v6.txt"] --> Gen_Internal

    Gen_Prompt --> Gen_LLM
    Gen_LLM --> Gen_ToolRes
    Gen_ToolRes --> Gen_Followup
    Gen_Followup -->|"repeated 2-3×"| Gen_Prompt

    Gen_Internal --> Raw_Out["output/raw/multi_turn.json"]
```

---

### Step 2: Annotation Internals

```mermaid
flowchart TD
    subgraph Ann_Internal["Annotation Pipeline"]
        Ann_Dedup["Dedup + Truncation Filter<br/>normalise speakable text<br/>dedup by first N user queries<br/>📄 annotator/dedup.py"]
        Ann_Schema["Schema Validation<br/>validate tool_call JSON<br/>check category ∈ domain.categories<br/>📄 utils/schema_utils.py"]
        Ann_Score["Per-Turn LLM Scoring<br/>model: deepseek-v4-flash · temp: 0.1<br/>threshold: 8 · hard_fail: 5<br/>📄 annotator/scorer.py"]
    end

    Raw_In["output/raw/multi_turn.json"] --> Ann_Internal
    Rubric_In["annotator_rubric_blocks.yaml"] --> Ann_Internal

    Ann_Dedup --> Ann_Schema
    Ann_Schema --> Ann_Score
    Ann_Score -->|"avg ≥ 8"| Pass_Out["output/final/multi_turn.json"]
    Ann_Score -->|"avg < 8 or hard-fail"| Fail_Out["Fail → Fix stage"]
```

---

### Step 5: Post-Processing Internals

```mermaid
flowchart TD
    subgraph Post_Internal["Post-Processing Pipeline"]
        Post_Assemble["Assemble Blocks<br/>2-3 blocks per conversation<br/>join on persona_id + dialect<br/>📄 post_processing/assemble_blocks.py"]
        Post_Split["Split<br/>eval_ratio: 1.0 (100% to eval)<br/>distillation_ratio: 0.0<br/>📄 post_processing/split.py"]
        Post_Rebalance["Rebalance<br/>tool:text ratio adjustment<br/>per-category contamination ctrl<br/>📄 post_processing/rebalance.py"]
        Post_Analysis["Analysis<br/>dataset balance report<br/>category coverage + enum dists<br/>📄 post_processing/analysis.py"]
    end

    Final_In["output/final/multi_turn.json"] --> Post_Internal
    Guard_In["guardrailing_blocks.json"] --> Post_Internal
    Schema_In["config/tool_schema.json"] --> Post_Internal

    Post_Assemble --> Post_Split
    Post_Split --> Post_Rebalance
    Post_Rebalance --> Post_Analysis

    Post_Internal --> Eval_Out["output/eval.json"]
    Post_Internal --> Train_Out["output/train.json"]
```

---

## Data Shapes

| Stage | Input | Output |
|---|---|---|
| Block Generation | config.yaml, personas.jsonl, context_v6.txt | output/raw/multi_turn.json |
| Guardrailing | config.yaml, corpus/fewshot | guardrailing_raw/guardrailing_blocks.json |
| Annotation | output/raw/multi_turn.json, rubric.yaml | output/final/multi_turn.json, multi_turn_scored.json |
| Fix | multi_turn_scored.json (failed) | output/fixed/multi_turn.json |
| Re-Annotation | output/fixed/multi_turn.json | output/rescored/multi_turn.json |
| Post-Processing | output/final/multi_turn.json, guard blocks | output/eval.json, output/train.json |

---

## Config Snapshot

| Parameter | Value |
|---|---|
| query model | deepseek/deepseek-v4-flash |
| answer model | deepseek/deepseek-v4-flash |
| annotator model | deepseek/deepseek-v4-flash |
| query temperature | 0.7 |
| answer temperature | 0.3 |
| followup temperature | 0.7 |
| annotator temperature | 0.1 |
| max_tokens (query/answer) | 8192 |
| batch_size | 50 |
| annotation threshold | 8 |
| hard_fail_threshold | 5 |
| insight_threshold | 5 |
| insight_hard_fail_floor | 2 |
| followups per block | 2-3 |
| blocks per conversation | 2-3 |
| samples_per_combo | 1 |
| type_ratio | tool: 0.5, nlr: 0.5 |
| eval_ratio | 1.0 |
| distillation_ratio | 0.0 |
| guardrailing samples | 200 |
| guardrailing query_source | corpus |
| capture_response | enabled |
| guardrail_in_generation | enabled |
| tool_call_correction | enabled |
