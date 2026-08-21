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
        Gen_Query["Query Generation<br/>deepseek-v4-flash · temp 0.7"]
        Gen_Answer["Answer Generation<br/>deepseek-v4-flash · temp 0.3"]
        Gen_Tool["Tool Result + Response<br/>synthesise result → brief reply"]
    end

    subgraph Guardrailing["Step 1.5: Guardrailing"]
        Guard_Gen["Adversarial Query Gen<br/>corpus mode · 200 samples"]
        Guard_Verify["Guard Verification<br/>tag_guardrail_topics signpost"]
    end

    subgraph Annotation["Step 2: Annotation"]
        Ann_Dedup["Dedup + Truncation Filter<br/>normalised query matching"]
        Ann_Score["Per-Turn LLM Scoring<br/>deepseek-v4-flash · temp 0.1"]
        Ann_Filter["Threshold Filter<br/>avg ≥ 8 · hard-fail floor 5"]
    end

    subgraph Fix["Step 3: Fix Failed"]
        Fix_Rewrite["LLM Turn Rewrite<br/>deepseek-v4-flash · temp 0.3"]
        Fix_Validate["Tool-Call Correction<br/>schema re-validation"]
    end

    ReAnn["Step 4: Re-Annotate Fixed<br/>same scorer · merge with passing"]

    subgraph PostProc["Step 5: Post-Processing"]
        Post_Assemble["Assemble Blocks<br/>2-3 blocks per conversation"]
        Post_Split["Train/Val/Eval Split<br/>100% eval (ric_v9)"]
        Post_Rebalance["Rebalance<br/>tool:text ratio · contamination"]
        Post_Analysis["Analysis Report<br/>balance · coverage · issues"]
    end

    subgraph Outputs
        Out_Eval["output/eval.json"]
        Out_Train["output/train.json"]
        Out_Report["report.md"]
    end

    Inputs --> Generation
    Config --> Guardrailing
    Gen_Query --> Gen_Answer --> Gen_Tool
    Gen_Tool -->|"per block · 2-3 follow-ups"| Gen_Query
    Guard_Gen --> Guard_Verify

    Generation -->|"raw blocks"| Annotation
    Guardrailing -->|"guard blocks"| Annotation
    Ann_Dedup --> Ann_Score --> Ann_Filter
    Ann_Filter -->|"pass · avg ≥ 8"| ReAnn
    Ann_Filter -->|"fail"| Fix

    Fix_Rewrite --> Fix_Validate
    Fix --> ReAnn
    ReAnn --> PostProc

    Post_Assemble --> Post_Split --> Post_Rebalance --> Post_Analysis
    PostProc --> Outputs
```

### Step 1: Block Generation Internals

```mermaid
flowchart TD
    subgraph Gen_Internal["Block Generation Pipeline"]
        Gen_Combo["Cartesian Combo Build<br/>dialect × type × topic × emotion<br/>samples_per_combo: 1"]
        Gen_QueryStep["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7 · max_tokens: 8192"]
        Gen_AnswerStep["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3 · tool_choice: auto"]
        Gen_ToolStep["Tool Result + Response<br/>synthesise realistic tool result<br/>brief professional response"]
        Gen_FollowUp["Follow-up Turn Loop<br/>followup_temp: 0.7<br/>same topic · 2-3 turns"]
    end

    Gen_Combo --> Gen_QueryStep
    Gen_QueryStep --> Gen_AnswerStep
    Gen_AnswerStep --> Gen_ToolStep
    Gen_ToolStep --> Gen_FollowUp
    Gen_FollowUp -->|"per block · repeated 2-3×"| Gen_QueryStep
    Gen_FollowUp -->|"complete"| BlockPool["Block Pool<br/>output/raw/multi_turn.json"]
    Gen_FollowUp -->|"turn failed"| Retry["Retry / Drop"]
```

### Step 2: Annotation Internals

```mermaid
flowchart TD
    subgraph Ann_Internal["Annotation Pipeline"]
        Ann_DedupStep["Deduplication<br/>normalised first-N-turn query match<br/>annotator/dedup.py"]
        Ann_ValidateStep["Schema Validation<br/>category check · param validation<br/>utils/schema_utils.py"]
        Ann_ScoreStep["Per-Turn LLM Scoring<br/>model: deepseek-v4-flash · temp: 0.1<br/>metrics per turn type · batch 50"]
        Ann_FilterStep["Threshold Filter<br/>avg ≥ 8 · hard-fail floor 5<br/>insight ≥ 5 · insight floor 2"]
    end

    Ann_DedupStep --> Ann_ValidateStep --> Ann_ScoreStep
    Ann_ScoreStep -->|"retry · max 3 attempts"| Ann_ScoreStep
    Ann_ScoreStep --> Ann_FilterStep
    Ann_FilterStep -->|"pass"| PassOut["final/multi_turn.json"]
    Ann_FilterStep -->|"fail or hard-fail"| FailOut["→ Fix Stage"]
```

### Step 5: Post-Processing Internals

```mermaid
flowchart TD
    subgraph Post_Internal["Post-Processing Pipeline"]
        Post_AssembleStep["Assemble Blocks<br/>2-3 blocks/conv · join persona+dialect<br/>transition_weights · forbid_same_type_run"]
        Post_SplitStep["Train/Val/Eval Split<br/>ratios: 0% / 0% / 100%<br/>distillation vs benchmark format"]
        Post_RebalanceStep["Rebalance<br/>tool:text ratio · max contamination 20%<br/>per-category filtering"]
        Post_AnalysisStep["Analysis Report<br/>balance · enum distributions<br/>category coverage · keyword contamination"]
    end

    Post_AssembleStep --> Post_SplitStep --> Post_RebalanceStep --> Post_AnalysisStep
    Post_AnalysisStep --> EvalOut["output/eval.json"]
    Post_AnalysisStep --> TrainOut["output/train.json"]
    Post_AnalysisStep --> ReportOut["report.md"]
```

## Data Shapes

| Stage | Input | Output |
|---|---|---|
| Block Generation | config.yaml, personas.jsonl, context_v6.txt | output/raw/multi_turn.json |
| Guardrailing | config.yaml, fewshot corpus | guardrailing_raw/guardrailing_blocks.json |
| Annotation | output/raw/multi_turn.json, rubric.yaml | final/multi_turn.json, multi_turn_scored.json |
| Fix | multi_turn_scored.json (failed only) | fixed/multi_turn.json, fixed/passing/ |
| Re-Annotation | fixed/multi_turn.json | rescored/multi_turn.json |
| Post-Processing | final/multi_turn.json, guardrailing_blocks.json | eval.json, train.json, report.md |

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
| max_retries | 3 |
| samples_per_combo | 1 |
| followups per block | 2-3 |
| blocks per conversation | 2-3 |
| guardrailing samples | 200 |
| eval_ratio | 1.0 (100% eval) |
| distillation_ratio | 0.0 |
| base_url | openrouter.ai/api/v1 |
