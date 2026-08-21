# convai-lab Architecture

> Experiment lab for measuring the **convai** conversational-AI banking assistant.
> The lab consumes the product (pinned submodule); the product knows nothing about the lab.

## Overview

```mermaid
flowchart TD
    subgraph Inputs
        ENV[Environments<br/>e0–e16, visualise_data_v1/v2]
        PROMPT[Prompt Arms<br/>p0–p12 + sections/]
        DATA[Datasets<br/>corpora/ · scenarios/]
    end

    subgraph "1. Author"
        A1[Copy parent → new numbered arm]
        A2[Create setup JSON<br/>prompt_pN_env_eM.json]
        A1 --> A2
    end

    subgraph "2. Choose"
        C1[Select eval_params<br/>hard/chart/guardrail/suite_full]
        C2[Build scenario battery<br/>prompts_to_scenarios.py]
        C1 --> C2
    end

    subgraph "3. Run"
        R1[sweep.py — eval_params × cells matrix]
        R2[run_ceval.py — boot realtime-text]
        R3[Invoke convai-eval<br/>simulate + judge]
        R4[Record provenance manifest.json]
        R1 --> R2 --> R3 --> R4
    end

    subgraph "4. Read"
        V1[ceval_table.py — score vectors]
        V2[ceval_to_responses.py — adapt]
        V3[inspector.py + webapp]
        V1 --> V2 --> V3
    end

    ENV -->|frozen arms| A1
    PROMPT -->|prompt pN| A1
    A2 -->|setup JSON| C1
    DATA -->|corpora| C2
    C2 -->|ceval args| R1
    R4 -->|results/ceval/| V1
    V3 --> OUT[Evidence Outputs<br/>score vectors · viewer app]
```

## Pipeline Stages

### 1. Author (`environments/` · `prompt_arms/`)

| Step | What | Key detail |
|------|------|-----------|
| Copy parent | `cp -r environments/parent environments/eN+1` | Never edit an existing arm |
| Create setup | `runners/setups/experimental_tools/prompt_pN_env_eM.json` | Pairs prompt arm + environment |

An environment is a frozen snapshot: tools.py (schemas), logic.py (pure computation), manifest.py (lineage).
A prompt arm is a versioned system prompt from section files under `prompt_arms/sections/`.

### 2. Choose (`datasets/` · `runners/eval_params.py`)

| Step | What | Key detail |
|------|------|-----------|
| Select eval_params | Named parameter sets | `lab_prompts_hard`, `chart`, `guardrail`, `suite_full` |
| Build battery | `prompts_to_scenarios.py` | `--max-turns 3` via exchange_limit_controller |

### 3. Run (`runners/sweep.py`)

| Step | What | Key detail |
|------|------|-----------|
| sweep.py | Iterate matrix | Sequential cells (shared Postgres + port) |
| run_ceval.py | Boot realtime-text | `managed_realtime(cell.env)` via uvicorn |
| convai-eval | simulate + judge | Gemma-4-26B-A4B-it default · batch-size 4 |
| Provenance | manifest.json | lab SHA + product SHA + dirty flags |

### 4. Read (`view/`)

| Step | What | Key detail |
|------|------|-----------|
| ceval_table.py | Score vector per cell | Auto-fails + LLM rubric + cross-turn |
| ceval_to_responses.py | Adapt for viewer | Auto-run after each cell in sweep |
| inspector.py + webapp | Side-by-side comparison | Real chart components from pinned product |

## Data Shapes

| Artifact | Format | Location |
|----------|--------|----------|
| Setup JSON | `{"name": "prompt_p6_env_e14", "env": {...}}` | `runners/setups/experimental_tools/` |
| Eval params | Python dataclass → ceval command tail | `runners/eval_params.py` |
| Scenario battery | JSON array of openings | `datasets/scenarios/` |
| Run manifest | JSON with provenance + status | `results/ceval/<run_id>/manifest.json` |
| Responses | JSON adapted for viewer | `results/ceval/<run_id>/responses.json` |
| Score vector | Terminal table per cell | stdout from `view/ceval_table.py` |

## Config Snapshot

| Parameter | Value | Source |
|-----------|-------|--------|
| Default model | `google/gemma-4-26B-A4B-it` | `VLLM_MODEL` env / `runners/models.py` |
| Max turns (authored) | 3 | `eval_params.py` `_DEPTH` |
| Max turns (suite) | 8 (self-terminating) | convai-eval built-in |
| Batch size | 4 concurrent scenarios | ceval default |
| Python version | ≥3.12, <3.13 | `pyproject.toml` |
| Realtime port | 8001 | `runners/utils.py` |
| API URL | `http://localhost:8000` | `runners/utils.py` |

## Key Constraints

- **Freeze rule**: Once an arm produces citable results, it never changes (including bugs).
- **Provenance**: Every run records lab SHA, product SHA, evaluator SHA, and dirty flags.
- **One-way dependency**: Lab imports product; product imports nothing from lab.
- **Sequential cells**: One Postgres + one realtime port; each batch's reseed truncates globally.
- **No parallelism**: Cells cannot run concurrently; within a cell, scenarios batch at 4.
