# Architecture

## Pipeline Overview

```mermaid
flowchart TD
    subgraph Inputs
        Config["generation_plan_ric_v9.yaml"]
        Personas["persona_banking.jsonl"]
        Corpus["guardrailing corpus"]
    end

    subgraph Generation["Step 1: Generation"]
        Gen_Block["Block Generation<br/>model: deepseek-v4-flash<br/>batch: 50 · 2-3 followups"]
        Gen_Guard["Guardrailing Gen<br/>corpus mode · 200 samples<br/>balanced by primary tag"]
    end

    subgraph Annotation["Steps 2-4: Annotate & Fix"]
        Ann_Score["Annotation<br/>threshold: 8 · hard_fail: 5"]
        Ann_Fix["Fix Failed Turns<br/>model: deepseek-v4-flash · temp: 0.3"]
        Ann_Reann["Re-annotation<br/>merge passing + recovered"]
    end

    subgraph PostProcessing["Steps 5-8: Post-Processing"]
        Post_Assemble["Assemble Blocks<br/>2-3 blocks/conv · join on persona"]
        Post_Split["Split<br/>100% eval (ric_v9 config)"]
        Post_Rebalance["Rebalance<br/>tool:text ratio · contamination"]
        Post_Analysis["Analysis<br/>balance + coverage + contamination"]
    end

    subgraph Outputs
        Out_Eval["output/eval.json"]
        Out_Train["output/train.json"]
        Out_Val["output/val.json"]
    end

    Inputs --> Generation
    Gen_Block --> Gen_Guard
    Generation --> Annotation
    Ann_Score --> Ann_Fix
    Ann_Fix --> Ann_Reann
    Annotation --> PostProcessing
    Post_Assemble --> Post_Split
    Post_Split --> Post_Rebalance
    Post_Rebalance --> Post_Analysis
    PostProcessing --> Outputs
```

---

### Step 1: Generation Internals

```mermaid
flowchart TD
    subgraph BlockGen["Block Generation (per combo)"]
        BG_Query["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7 · max_tokens: 8192"]
        BG_Answer["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3 · tool_choice: auto"]
        BG_Tool["Tool Result + Response<br/>concierge DB execution<br/>correction: temp 0.1"]
        BG_Follow["Follow-up Turn<br/>same topic, no pivot<br/>followup_temp: 0.7"]
    end

    subgraph GuardGen["Guardrailing Generation"]
        GG_Sample["Balanced Corpus Sampling<br/>samples_total: 200"]
        GG_Tag["Tag Classification<br/>ADV, CORA, OT, TOX"]
        GG_Build["Block Builder<br/>tag_guardrail_topics call<br/>signpost response"]
    end

    BG_Query --> BG_Answer
    BG_Answer --> BG_Tool
    BG_Tool --> BG_Follow
    BG_Follow -->|"repeated 3-5×"| BG_Query

    GG_Sample --> GG_Tag
    GG_Tag --> GG_Build

    BG_Follow -->|"≥ min turns"| Pass_Pool["Block Pool ✓"]
    BG_Follow -->|"budget exhausted"| Dropped["Dropped ✗"]

    BlockGen --> RawOut["output/raw/multi_turn.json"]
    GuardGen --> GuardOut["guardrailing_blocks.json"]
```

---

### Steps 2-4: Annotation & Fix Internals

```mermaid
flowchart TD
    subgraph Annotate["Step 2: Annotation"]
        A_Dedup["Deduplication<br/>normalise_speakable<br/>remove_truncated"]
        A_Score["Per-Turn LLM Scoring<br/>model: deepseek-v4-flash<br/>temp: 0.1 · max_retries: 3"]
        A_Filter["Threshold Filter<br/>avg ≥ 8 · no metric ≤ 5<br/>insight gate: mean ≥ 5"]
    end

    subgraph Fix["Step 3: Fix Failed Turns"]
        F_Identify["Identify Failures<br/>separate pass/fail"]
        F_Rewrite["LLM Turn Rewrite<br/>model: deepseek-v4-flash<br/>fix_prompt: fix_turn_v2.txt"]
        F_Reground["Re-ground Tool Calls<br/>concierge DB re-execution<br/>persona-specific reseed"]
    end

    A_Dedup --> A_Score
    A_Score --> A_Filter
    A_Filter -->|"failed"| F_Identify
    A_Filter -->|"passed"| Final["output/final/multi_turn.json"]
    F_Identify --> F_Rewrite
    F_Rewrite --> F_Reground
    F_Reground -->|"Step 4: re-annotate"| A_Score
    F_Reground --> Final
```

---

### Steps 5-8: Post-Processing Internals

```mermaid
flowchart TD
    subgraph PostPipeline["Post-Processing Pipeline"]
        PP_Assemble["Assemble Blocks<br/>2-3 blocks/conv<br/>join: persona, dialect, date<br/>transition weights: tool/nlr/guard"]
        PP_Split["Split into Sets<br/>eval: 100% · seed: 42<br/>distill + benchmark format"]
        PP_Rebal["Rebalance Training Data<br/>tool:text ratio control<br/>per-category contamination"]
        PP_Anal["Dataset Analysis<br/>balance · enum dist<br/>category coverage<br/>keyword contamination"]
    end

    FinalIn["output/final/multi_turn.json"] --> PP_Assemble
    GuardIn["guardrailing_blocks.json"] --> PP_Assemble
    PP_Assemble --> PP_Split
    PP_Split --> PP_Rebal
    PP_Rebal --> PP_Anal

    PP_Split --> EvalOut["output/eval.json"]
    PP_Split --> TrainOut["output/train.json"]
    PP_Split --> ValOut["output/val.json"]
```

---

## Data Shapes

| Stage | Input | Output |
|---|---|---|
| Block Generation | config YAML, personas JSONL | output/raw/multi_turn.json |
| Guardrailing Gen | labelled corpus JSON | guardrailing_raw/guardrailing_blocks.json |
| Annotation | output/raw/multi_turn.json | output/final/multi_turn.json, multi_turn_scored.json |
| Fix | multi_turn_scored.json (failed) | fixed/multi_turn.json |
| Assemble | final/multi_turn.json + guardrailing_blocks.json | final/multi_turn.json (overwritten) |
| Split | final/multi_turn.json | eval.json, train.json, val.json |
| Rebalance | output/train.json | output/train.json (filtered) |
| Analysis | output/train.json | report.md |

---

## Config Snapshot

| Parameter | Value | Source |
|---|---|---|
| query model | deepseek/deepseek-v4-flash | generator.query.model |
| answer model | deepseek/deepseek-v4-flash | generator.answer.model |
| annotator model | deepseek/deepseek-v4-flash | annotator.model |
| fixer model | deepseek/deepseek-v4-flash | fixer.model |
| query temp | 0.7 | generator.query.temperature |
| answer temp | 0.3 | generator.answer.temperature |
| followup temp | 0.7 | generator.answer.followup_temperature |
| annotator temp | 0.1 | annotator.temperature |
| fixer temp | 0.3 | fixer.temperature |
| batch_size | 50 | generator.batch_size |
| threshold | 8 | annotator.threshold |
| hard_fail_threshold | 5 | annotator.hard_fail_threshold |
| insight_threshold | 5 | annotator.insight_threshold |
| insight_hard_fail_floor | 2 | annotator.insight_hard_fail_floor |
| max_retries | 3 | annotator.max_retries |
| followups | min: 2, max: 3 | pipeline.block.followups |
| blocks_per_conversation | min: 2, max: 3 | pipeline.assemble |
| samples_per_combo | 1 | taxonomy.scenarios[0] |
| guardrailing samples | 200 | guardrailing.samples_total |
| eval_ratio | 1.0 | output.eval_ratio |
| base_url | openrouter.ai/api/v1 | generator.query.base_url |
| concierge enabled | true | generator.concierge.enabled |
| capture_response | true | generator.capture_response.enabled |
| guardrail_in_generation | true | generator.guardrail_in_generation.enabled |
