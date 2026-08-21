# Architecture

## Pipeline Overview

```mermaid
flowchart TD
    subgraph Inputs
        Config["generation_plan_ric_v10.yaml"]
        Personas["persona_banking.jsonl"]
        Concierge["Concierge PostgreSQL DB"]
    end

    subgraph Generation["Step 1: Generation"]
        Gen_Query["Query Generation<br/>model: deepseek-v4-flash<br/>temp: 0.7"]
        Gen_Answer["Answer Generation<br/>model: deepseek-v4-flash<br/>temp: 0.3"]
        Gen_Block["Block Pool Output<br/>followups: 2-3 per block"]
    end

    subgraph Guardrailing["Step 1.5: Guardrailing"]
        Guard_Gen["Adversarial Query Gen<br/>corpus mode · 200 samples"]
        Guard_Verify["Guard Verification<br/>tag_guardrail_topics"]
    end

    subgraph Annotation["Step 2: Annotation"]
        Ann_Dedup["Dedup & Schema Validate"]
        Ann_Score["LLM Scoring (ensemble)<br/>minimax-m3 + glm-5.2<br/>temp: 0.1"]
        Ann_Pass["Pass ≥8.0"]
        Ann_Fail["Fail <8.0"]
    end

    subgraph Fix["Step 3: Fix"]
        Fix_Turn["Turn-Level Fixer<br/>model: deepseek-v4-flash<br/>temp: 0.3"]
    end

    subgraph ReAnnotation["Step 4: Re-annotation"]
        ReAnn_Dedup["Dedup & Validate"]
        ReAnn_Score["LLM Scoring (ensemble)"]
        ReAnn_Pass["Pass ≥8.0"]
        ReAnn_Fail["Fail <8.0"]
    end

    subgraph PostProcessing["Step 5: Post-Processing"]
        Post_Merge["Merge Pass + Re-scored"]
        Post_Assemble["Assemble Blocks<br/>2-3 blocks/conv"]
        Post_Split["Split<br/>eval 100%"]
        Post_Rebalance["Rebalance<br/>tool/nlr ratio"]
        Post_Analysis["Analysis Report"]
    end

    subgraph Outputs
        Train["train.json"]
        Eval["eval.json"]
        Val["val.json"]
    end

    Config --> Generation
    Personas --> Generation
    Concierge --> Generation
    Config --> Guardrailing

    Gen_Query --> Gen_Answer
    Gen_Answer --> Gen_Block
    Guard_Gen --> Guard_Verify

    Generation --> Annotation
    Ann_Dedup --> Ann_Score
    Ann_Score -->|pass| Ann_Pass
    Ann_Score -->|fail| Ann_Fail

    Ann_Fail --> Fix
    Fix --> ReAnnotation
    ReAnn_Dedup --> ReAnn_Score
    ReAnn_Score -->|pass| ReAnn_Pass
    ReAnn_Score -->|fail| ReAnn_Fail

    Ann_Pass --> PostProcessing
    ReAnn_Pass --> PostProcessing
    Guardrailing -.->|guard blocks| PostProcessing

    Post_Merge --> Post_Assemble
    Post_Assemble --> Post_Split
    Post_Split --> Post_Rebalance
    Post_Rebalance --> Post_Analysis

    PostProcessing --> Train
    PostProcessing --> Eval
    PostProcessing --> Val

    ReAnn_Fail -->|discarded| Discard["Discarded"]
```

---

### Step 1: Generation Internals

```mermaid
flowchart TD
    subgraph Gen_Internal["Generation Pipeline"]
        Gen_QueryGen["Query Generation<br/>model: deepseek/deepseek-v4-flash<br/>temp: 0.7 · max_tokens: 8192<br/>📄 generator/run_generation.py"]
        Gen_AnswerGen["Answer Generation<br/>model: deepseek/deepseek-v4-flash<br/>temp: 0.3 · followup_temp: 0.7<br/>tool_call_correction: enabled"]
        Gen_MultiTurn["Multi-Turn Block Gen<br/>followups: 2-3 per block<br/>type_ratio: tool 50% / nlr 50%<br/>📄 generator/multi_turn_gen.py"]
        Gen_Concierge["Concierge DB Execution<br/>real PostgreSQL tool results<br/>persona_db_sample: 1<br/>📄 generator/concierge_executor.py"]
        Gen_Output["→ output/raw/multi_turn.json"]
    end

    Gen_QueryGen --> Gen_AnswerGen
    Gen_AnswerGen --> Gen_MultiTurn
    Gen_MultiTurn --> Gen_Concierge
    Gen_Concierge --> Gen_Output
    Gen_Output -->|"per combo · dialect × emotion × style × topic"| Gen_QueryGen
```

---

### Step 2: Annotation Internals

```mermaid
flowchart TD
    subgraph Ann_Internal["Annotation Pipeline"]
        Ann_Dedup2["Deduplication<br/>normalise first N user turns<br/>remove exact-match queries<br/>📄 annotator/dedup.py"]
        Ann_Truncated["Remove Truncated & Normalise<br/>strip incomplete responses<br/>normalise speakable text"]
        Ann_Scoring["Per-Turn LLM Scoring<br/>ensemble: minimax-m3 + glm-5.2<br/>temp: 0.1 · max_retries: 3<br/>📄 annotator/scorer.py"]
        Ann_Merge["Merge Scores (ensemble)<br/>min avg per turn across models<br/>OR hard_fail flags<br/>📄 annotator/merge_scores.py"]
        Ann_PassOut["Pass (avg ≥8.0 & no hard_fail)"]
        Ann_FailOut["Fail (<8.0 or hard_fail)"]
    end

    Rubric["annotator_rubric_blocks.yaml"] --> Ann_Scoring

    Ann_Dedup2 --> Ann_Truncated
    Ann_Truncated --> Ann_Scoring
    Ann_Scoring -->|"retry · max 3 attempts"| Ann_Scoring
    Ann_Scoring --> Ann_Merge
    Ann_Merge -->|pass| Ann_PassOut
    Ann_Merge -->|fail| Ann_FailOut
```

---

### Step 5: Post-Processing Internals

```mermaid
flowchart TD
    subgraph Post_Internal["Post-Processing Pipeline"]
        Post_Merge2["Merge Outputs<br/>ann pass + re-scored pass → final/<br/>combine per-scenario JSONs"]
        Post_Assemble2["Assemble Blocks<br/>2-3 blocks/conversation<br/>join: persona_id, dialect, date<br/>📄 post_processing/assemble_blocks.py"]
        Post_Validate["Validate Blocks<br/>structural/flow validation<br/>drop invalid stitched convos<br/>📄 post_processing/validate_blocks.py"]
        Post_Split2["Split<br/>distillation / eval / validation<br/>ratio: 0% / 100% / 0%<br/>📄 post_processing/split.py"]
        Post_Rebalance2["Rebalance<br/>tool/nlr ratio · category caps<br/>max contamination: 20%<br/>📄 post_processing/rebalance.py"]
        Post_Analysis2["Analysis Report<br/>Section 1-6 breakdown<br/>📄 post_processing/analysis.py"]
    end

    GuardBlocks["guardrailing_blocks.json"] --> Post_Assemble2

    Post_Merge2 --> Post_Assemble2
    Post_Assemble2 --> Post_Validate
    Post_Validate --> Post_Split2
    Post_Split2 --> Post_Rebalance2
    Post_Rebalance2 --> Post_Analysis2

    Post_Split2 --> Train2["output/train.json"]
    Post_Split2 --> Eval2["output/eval.json"]
    Post_Split2 --> Val2["output/val.json"]
```

---

## Data Shapes

| Stage | Input | Output |
|---|---|---|
| Generation | config YAML, persona_banking.jsonl, Concierge DB | output/raw/multi_turn.json |
| Guardrailing | config YAML, corpus file | guardrailing_raw/guardrailing_blocks.json |
| Annotation | output/raw/multi_turn.json | output/ann/multi_turn.json + _scored.json + summary.json |
| Fix | output/ann/*_scored.json (failed) | output/fixed/multi_turn.json + passing/ |
| Re-annotation | output/fixed/multi_turn.json | output/rescored/multi_turn.json + summary.json |
| Post-Processing (Merge) | ann/ + rescored/ + passing/ | final/multi_turn.json |
| Post-Processing (Assemble) | final/multi_turn.json + guardrailing_blocks.json | final/multi_turn.json (overwritten) |
| Post-Processing (Split) | final/multi_turn.json | train.json, eval.json, val.json |
| Post-Processing (Rebalance) | train.json | train.json (overwritten) |
| Post-Processing (Analysis) | train.json | terminal report |

---

## Config Snapshot

| Parameter | Value | Source |
|---|---|---|
| Query model | deepseek/deepseek-v4-flash | generator.query.model |
| Query temperature | 0.7 | generator.query.temperature |
| Answer model | deepseek/deepseek-v4-flash | generator.answer.model |
| Answer temperature | 0.3 | generator.answer.temperature |
| Answer followup_temperature | 0.7 | generator.answer.followup_temperature |
| Fixer model | deepseek/deepseek-v4-flash | fixer.model |
| Fixer temperature | 0.3 | fixer.temperature |
| Annotator models | minimax/minimax-m3, z-ai/glm-5.2 | annotator.models |
| Annotator temperature | 0.1 | annotator.temperature |
| Pass threshold | 8.0 | annotator.threshold |
| Hard fail threshold | 5 | annotator.hard_fail_threshold |
| Insight threshold | 5 | annotator.insight_threshold |
| Batch size | 50 | generator.batch_size |
| Max retries (scoring) | 3 | annotator.max_retries |
| Block followups | min: 2, max: 3 | taxonomy.scenarios[0].pipeline[0].followups |
| Blocks per conversation | min: 2, max: 3 | taxonomy.scenarios[0].pipeline[1].blocks_per_conversation |
| Type ratio | tool: 0.5, nlr: 0.5 | taxonomy.scenarios[0].pipeline[0].type_ratio |
| Guardrailing samples | 200 | guardrailing.samples_total |
| Guardrailing query source | corpus | guardrailing.query_source |
| Concierge enabled | true | generator.concierge.enabled |
| Capture response enabled | true | generator.capture_response.enabled |
| Guardrail in generation | true | generator.guardrail_in_generation.enabled |
| Output split ratio | 0% distill / 100% eval / 0% val | output.distillation_ratio / eval_ratio / validation_ratio |
