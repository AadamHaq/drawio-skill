# Synthetic Banking Dataset Pipeline — Architecture

## Overview

```mermaid
flowchart TD
    subgraph Inputs
        CONFIG["Generation Plan<br/>generation_plan_ric_v9.yaml"]
        RUBRIC["Annotator Rubric<br/>annotator_rubric_blocks.yaml"]
        PERSONA["Personas<br/>persona_banking.jsonl"]
        SCHEMA["Tool Schema<br/>tool_schema.json / Concierge DB"]
    end

    subgraph "STEP 1: Block Generation"
        QUERY["Query Gen<br/>deepseek-v4-flash · temp 0.7"]
        ANSWER["Answer Gen<br/>deepseek-v4-flash · temp 0.3<br/>tool_choice=auto"]
        TOOL["Tool Result + Response<br/>deepseek-v4-flash · temp 0.3"]
    end

    GUARD["STEP 1.5: Guardrailing<br/>adversarial block gen"]

    ANN["STEP 2: Annotation<br/>per-turn scoring (1-10)<br/>threshold 8 · hard-fail ≤5"]
    FIX["STEP 3: Fix<br/>LLM correction of failed turns"]
    REANN["STEP 4: Re-Annotation<br/>score fixed samples"]

    subgraph "Post-Processing"
        ASSEMBLE["Assemble Blocks<br/>2-3 blocks/conv · transition weights"]
        SPLIT["Split<br/>train / val / eval"]
        REBALANCE["Rebalance<br/>tool:text ratio · contamination"]
        ANALYSIS["Analysis<br/>coverage · balance report"]
    end

    subgraph Outputs
        EVAL["eval.json<br/>benchmark format"]
        TRAIN["train.json<br/>distillation format"]
    end

    CONFIG --> QUERY
    PERSONA --> QUERY
    SCHEMA --> ANSWER
    QUERY --> ANSWER --> TOOL
    TOOL -->|raw blocks| ANN
    RUBRIC --> ANN
    GUARD -->|guard pool| ASSEMBLE
    ANN -->|failed| FIX
    ANN -->|passed| ASSEMBLE
    FIX --> REANN
    REANN -->|recovered| ASSEMBLE
    ASSEMBLE --> SPLIT --> REBALANCE --> ANALYSIS
    SPLIT --> EVAL
    REBALANCE --> TRAIN
```

## Generation Detail

```mermaid
flowchart TD
    subgraph Inputs
        CFG["Generation Plan<br/>taxonomy · models · pipeline"]
        PER["Personas<br/>persona_banking.jsonl"]
        SCH["Tool Schema<br/>Concierge DB or JSON"]
    end

    COMBO["Build Combos<br/>dialect × type × topic × emotion × typing_style<br/>samples_per_combo=1 · batch_size=50"]

    subgraph "Per-Block Generation Loop"
        Q["1. Query Generation<br/>deepseek-v4-flash · temp 0.7<br/>prompt: generate_queries_block.txt"]
        A["2. Answer Generation<br/>deepseek-v4-flash · temp 0.3<br/>tools=schema · tool_choice=auto"]
        TR["3a. Tool Result Synthesis<br/>prompt: generate_tool_result.txt<br/>realistic values from schema"]
        AR["3b. Assistant Response<br/>grounded narration · max 4 sentences"]
        FU["4. Follow-up Turns (×2-3)<br/>followup_temperature=0.7<br/>same topic · drop+retry on failure"]
        VAL["5. Structural Validation<br/>validate_conversation_structure()"]
    end

    OUT["output/raw/multi_turn.json<br/>block pool"]

    CFG --> COMBO
    PER --> COMBO
    SCH --> COMBO
    COMBO --> Q --> A --> TR --> AR --> FU --> VAL
    VAL --> OUT
```

## Data Shapes

| Stage | Input Format | Output Format |
|-------|-------------|---------------|
| Generation | Cartesian combos (persona × dialect × type × topic × emotion × typing_style) | `{"messages": [...], "metadata": {...}}` blocks |
| Guardrailing | Tag sets (adversarial topics) | `{"messages": [...], "metadata": {...}}` guard blocks |
| Annotation | Raw block JSON | Scored blocks with per-turn `scores` dict |
| Fix | Failed blocks (score < threshold) | Rewritten blocks (same schema) |
| Assemble | Passing blocks + guard pool | Multi-turn conversations (2-3 blocks stitched) |
| Split | Assembled conversations | train.json (distillation) / eval.json (benchmark) |
| Rebalance | train.json | Filtered train.json (balanced tool:text ratio) |
| Analysis | train.json | Markdown report (coverage, contamination, balance) |

## Config Snapshot

| Key | Value | Source |
|-----|-------|--------|
| Query model | `deepseek/deepseek-v4-flash` | `generator.query.model` |
| Answer model | `deepseek/deepseek-v4-flash` | `generator.answer.model` |
| Annotator model | `deepseek/deepseek-v4-flash` | `annotator.model` |
| Query temperature | 0.7 | `generator.query.temperature` |
| Answer temperature | 0.3 | `generator.answer.temperature` |
| Follow-up temperature | 0.7 | `generator.answer.followup_temperature` |
| Annotation threshold | 8 | `annotator.threshold` |
| Hard-fail threshold | 5 | `annotator.hard_fail_threshold` |
| Batch size | 50 | `generator.batch_size` |
| Follow-ups per block | 2-3 | `pipeline[0].followups` |
| Blocks per conversation | 2-3 | `pipeline[1].blocks_per_conversation` |
| Context prompt | `generator/prompts/eval/context_v6.txt` | `domain.context_prompt` |
| Rubric | `config/annotator_rubric_blocks.yaml` | `annotator.rubric_path` |
| Output ratio | 100% eval | `output.eval_ratio` |
| Guardrailing | enabled | `guardrailing.enabled` |
| Capture response | enabled (tool call format) | `generator.capture_response.enabled` |

## Annotation Metrics by Turn Type

| Turn Type | Core Metrics |
|-----------|-------------|
| opening tool | naturalness, parameter_coverage, when2call, tool_result_accuracy, groundedness, assumption_surfacing |
| opening nlr | naturalness, when2call, response_quality, professionalism, groundedness |
| opening clarify | naturalness, when2call, clarification_quality |
| opening guardrail | naturalness, when2call, tag_accuracy |
| followup tool | + context_coherence, topic_coherence |
| followup nlr | + context_coherence, topic_coherence |
| followup clarify | + context_coherence, topic_coherence |
| followup guardrail | + context_coherence |

## Pipeline Steps (run_pipeline.sh)

| Step | Module | Description |
|------|--------|-------------|
| 1 | `generator.run_generation` | Build combo grid, generate blocks (query → answer → tool result) |
| 1.5 | `guardrailing.run_generation` | Adversarial guardrail block pool (optional) |
| 2 | `annotator.run_annotation` | Score each turn (dedup + schema validate + LLM score) |
| 3 | `generator.run_fix` | LLM-rewrite failed turns preserving context |
| 4 | `annotator.run_annotation` | Re-score fixed samples (ensemble merge: min per turn) |
| — | Merge | Combine passed + recovered → final/ |
| — | `post_processing.assemble_blocks` | Stitch blocks into conversations (transition weights) |
| — | `post_processing.split` | Shuffle + split into train/val/eval |
| — | `post_processing.rebalance` | Filter broken exercises, adjust ratios |
| — | `post_processing.analysis` | Generate coverage/balance report |
