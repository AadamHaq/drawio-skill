# Architecture

## Service Map Overview

```mermaid
flowchart TD
    subgraph Client["Client Layer"]
        Web["Web Frontend<br/>React · Vite :3000<br/>LiveKit Client SDK"]
    end

    subgraph Gateway["Gateway Layer"]
        API["API Service<br/>FastAPI :8000<br/>Auth · Sessions · BoA"]
    end

    subgraph Services["Service Layer"]
        RT_Text["Realtime-Text<br/>WebSocket chat<br/>OpenAI / Cascade pipeline"]
        RT_Voice["Realtime-Voice<br/>Pipecat voice pipeline<br/>STT → LLM → TTS"]
    end

    subgraph Workers["Worker Layer (GPU)"]
        LLM["LLM (vLLM)<br/>gemma-4-26B-A4B-it<br/>OpenAI /v1 · LMCache"]
        STT["STT (Triton)<br/>nemotron_asr<br/>gRPC streaming"]
        TTS["TTS (Triton)<br/>chatterbox_tts<br/>gRPC decoupled"]
        Guards["Guardrails (Triton)<br/>prompt_injection · language<br/>multi_guard · PII"]
    end

    subgraph Infra["Infrastructure"]
        LiveKit["LiveKit<br/>WebRTC SFU :7880"]
        Postgres[("PostgreSQL :5432")]
        Redis[("Redis :6379")]
    end

    Web -->|"REST /api"| API
    Web -->|"WebSocket"| RT_Text
    Web -->|"WebRTC"| LiveKit

    API -->|"queries"| Postgres
    API -->|"sessions"| Redis

    RT_Text -->|"HTTP tools"| API
    RT_Text -->|"OpenAI /v1"| LLM
    RT_Text -->|"gRPC guard"| Guards

    RT_Voice -->|"HTTP tools"| API
    RT_Voice -->|"OpenAI /v1"| LLM
    RT_Voice -->|"gRPC audio"| STT
    RT_Voice -->|"gRPC text"| TTS
    RT_Voice -->|"gRPC guard"| Guards
    RT_Voice <-->|"audio frames"| LiveKit

    LiveKit -->|"rooms"| Redis
    LLM -->|"KV cache"| Redis
```

## Voice Pipeline (Cascade Mode)

```mermaid
flowchart TD
    Client["Web Client<br/>LiveKit SDK · WebRTC"]
    LK["LiveKit SFU<br/>signaling + media :7880"]

    subgraph VoiceWorker["Realtime-Voice Worker"]
        VAD["NeMo MarbleNet VAD<br/>confidence: 0.5<br/>start: 0.2s · stop: 0.7s"]
        STT_Step["STT (Triton gRPC)<br/>nemotron_asr · 80ms chunks<br/>streaming sequence batch"]
        Turn["SmartTurn v3<br/>silence: 1.5s · timeout: 2.0s"]
        GuardIn["Input Guardrails<br/>language · prompt_injection<br/>multi_guard"]
        LLM_Step["LLM (vLLM OpenAI /v1)<br/>gemma-4-26B-A4B-it<br/>tool calling · context"]
        GuardOut["Output Guardrails<br/>multi_guard (fail-closed)"]
        TTS_Step["TTS (Triton gRPC)<br/>chatterbox_tts · decoupled<br/>soft: 100 · max: 150 chars"]
    end

    APIBox["API Service<br/>tool execution (transactions)"]

    Client -->|"WebRTC"| LK
    LK -->|"audio frames"| VAD
    VAD --> STT_Step
    STT_Step --> Turn
    Turn --> GuardIn
    GuardIn -->|"pass"| LLM_Step
    LLM_Step --> GuardOut
    GuardOut -->|"pass"| TTS_Step
    TTS_Step -->|"audio out"| LK
    LLM_Step -->|"tool calls"| APIBox
```

## Pipeline Modes

```mermaid
flowchart LR
    subgraph Cascade["mode: cascade"]
        C_STT["STT<br/>(Triton)"] --> C_LLM["LLM<br/>(vLLM)"] --> C_TTS["TTS<br/>(Triton)"]
    end

    subgraph OpenAI["mode: openai"]
        O_RT["OpenAI Realtime API<br/>gpt-realtime · shimmer voice<br/>native function calling"]
    end

    Config["tilt_config.json<br/>pipeline-type"] -->|"cascade"| Cascade
    Config -->|"openai"| OpenAI
```

## Data Shapes

| Stage | Input | Output |
|---|---|---|
| Web Client | User speech / text | WebRTC audio / WebSocket messages |
| LiveKit | WebRTC stream | Audio frames to worker |
| VAD | Raw audio | Speech segments |
| STT | Audio frames (80ms) | Interim + final transcriptions |
| SmartTurn | Transcription stream | Complete user utterance |
| Guardrails (input) | User text | pass / blocked verdict |
| LLM | Conversation context + tools | Assistant response (streamed) |
| Guardrails (output) | Assistant text | pass / blocked verdict |
| TTS | Text chunks (≤150 chars) | Streamed PCM audio |
| API Tools | Tool call params | Transaction data, charts |

## Config Snapshot

| Parameter | Value | Source |
|---|---|---|
| LLM model | gemma-4-26B-A4B-it | tilt_config.json |
| STT model | nemotron_asr | tilt_config.json |
| TTS model | chatterbox_tts | tilt_config.json |
| Pipeline type | cascade / openai | tilt_config.json |
| VAD confidence | 0.5 | pipeline.py |
| VAD start/stop | 0.2s / 0.7s | pipeline.py |
| SmartTurn silence | 1.5s | pipeline.py |
| TTS soft split | 100 chars | triton.py |
| TTS max length | 150 chars | triton.py |
| STT chunk size | 80ms | TritonSTTClient |
| Session TTL | 900s | values.yaml |
| API port | 8000 | Dockerfile |
| LiveKit port | 7880 | values.yaml |

## Service Dependencies

| Service | Depends On | Protocol |
|---|---|---|
| Web | API, LiveKit, Realtime-Text | HTTP, WebRTC, WebSocket |
| API | PostgreSQL, Redis | SQL, Redis |
| Realtime-Text | API, LLM, Guardrails | HTTP, HTTP, gRPC |
| Realtime-Voice | API, LLM, STT, TTS, Guardrails, LiveKit | HTTP, HTTP, gRPC, gRPC, gRPC, WebSocket |
| LLM | Redis (KV cache) | Redis |
| LiveKit | Redis | Redis |

## Infrastructure

| Component | Image | Purpose |
|---|---|---|
| PostgreSQL | postgres:16-alpine | Conversations, users, accounts |
| Redis | redis:7-alpine | Sessions, LiveKit rooms, LMCache KV |
| LiveKit | livekit/livekit-server | WebRTC SFU, signaling |
| vLLM | vllm/vllm-openai:v0.25 | LLM serving (OpenAI-compatible) |
| Triton STT | tritonserver:26.03 | Speech-to-text inference |
| Triton TTS | tritonserver:26.06 | Text-to-speech inference |
| Triton Guards | tritonserver | Safety model inference |
