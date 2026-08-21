# Architecture — Concierge (Conversational AI Platform)

Financial conversational AI platform with real-time voice and text interactions, deployed on Kubernetes with Tilt for local development.

## Service Map

```mermaid
flowchart TD
    subgraph Client["Client Layer"]
        Web["Web UI<br/>React SPA · :3000<br/>LiveKit JS SDK (WebRTC)"]
    end

    subgraph Gateway["Gateway Layer"]
        API["API Service<br/>FastAPI · :8000<br/>Auth + BoA Integration"]
    end

    subgraph Services["Application Services"]
        RT_Text["Realtime-Text<br/>WebSocket handler<br/>ConversationProcessor<br/>Voice escalation"]
        RT_Voice["Realtime-Voice<br/>Cascade pipeline (STT→LLM→TTS)<br/>OpenAI Realtime pipeline<br/>LiveKit transport + VAD"]
    end

    subgraph Inference["Inference Workers (cascade mode)"]
        LLM["LLM (vLLM)<br/>gemma-4-26B-A4B-it · :8000<br/>OpenAI-compat API + tools"]
        Guardrails["Guardrails (Triton)<br/>prompt_injection · multi_guard<br/>pii_guard · gRPC :8001"]
        STT["STT (Triton)<br/>nemotron_asr · gRPC :8001<br/>NeMo 0.6B streaming"]
        TTS["TTS (Triton)<br/>chatterbox_tts · gRPC :8001<br/>LoRA + ACI + CUDA graphs"]
    end

    subgraph Infra["Infrastructure"]
        Postgres[("PostgreSQL<br/>:5432")]
        Redis[("Redis<br/>:6379")]
        LiveKit[("LiveKit<br/>:7880 (WebRTC SFU)")]
    end

    Web -->|"REST /api/v1"| API
    Web -.->|"WebSocket /ws"| RT_Text
    Web -.->|"WebRTC signalling"| LiveKit

    API -->|"queries"| Postgres
    API -->|"sessions"| Redis

    RT_Text -->|"tools + convos"| API
    RT_Voice -->|"tools + convos"| API

    RT_Text -->|"OpenAI-compat /v1"| LLM
    RT_Voice -->|"OpenAI-compat /v1"| LLM

    RT_Text ==>|"gRPC guards"| Guardrails
    RT_Voice ==>|"gRPC guards"| Guardrails

    RT_Voice ==>|"audio frames"| STT
    RT_Voice ==>|"text → speech"| TTS

    RT_Voice -.->|"audio out"| LiveKit
    LiveKit -.->|"audio in"| RT_Voice

    RT_Text -->|"room tokens"| LiveKit
    LiveKit -->|"room state"| Redis
```

## Voice Pipeline (Cascade Mode)

```mermaid
flowchart TD
    Browser["Browser<br/>LiveKit JS SDK"]
    LK["LiveKit Server<br/>WebRTC SFU · :7880"]

    subgraph Worker["Realtime-Voice Worker"]
        VAD["MarbleNet VAD<br/>confidence: 0.5 · stop: 0.7s"]
        SmartTurn["SmartTurn v3<br/>silence fallback: 1.5s"]
        ConvProc["ConversationProcessor<br/>system prompt v8 · tool calling"]
        Relay["TranscriptionRelay<br/>+ TTSTimingRelay"]
    end

    STT_svc["STT (Triton)<br/>nemotron_asr<br/>chunk: 80ms · preroll: 300ms"]
    LLM_svc["LLM (vLLM)<br/>gemma-4-26B-A4B-it<br/>prefix caching + chunked prefill"]
    TTS_svc["TTS (Triton)<br/>chatterbox_tts<br/>LoRA + ACI + CUDA graphs"]
    Guard_svc["Guardrails (Triton)<br/>prompt_inj + multi_guard + pii<br/>gRPC :8001 · threshold: 0.8"]
    API_svc["API Service<br/>tool execution + conversations"]

    Browser -.->|"WebRTC audio"| LK
    LK -.->|"audio frames (WS)"| Worker

    Worker ==>|"audio chunks"| STT_svc
    STT_svc ==>|"transcription"| Worker

    Worker -->|"prompt + context"| LLM_svc
    LLM_svc -->|"token stream"| Worker

    Worker ==>|"LLM text chunks"| TTS_svc
    TTS_svc -.->|"audio → client"| LK

    Worker ==>|"input/output rail"| Guard_svc
    Worker -->|"tool calls"| API_svc

    LK -.->|"audio out"| Browser
```

## Text Pipeline

```mermaid
flowchart TD
    Browser_T["Browser<br/>React SPA"]
    RT_T["Realtime-Text<br/>WebSocket handler"]
    LLM_T["LLM (vLLM)<br/>gemma-4-26B-A4B-it"]
    Guard_T["Guardrails (Triton)<br/>input rail"]
    API_T["API Service<br/>tool execution"]

    Browser_T -.->|"WebSocket /ws"| RT_T
    RT_T ==>|"gRPC input rail"| Guard_T
    RT_T -->|"OpenAI-compat /v1"| LLM_T
    LLM_T -->|"token stream"| RT_T
    RT_T -->|"tool calls"| API_T
    API_T -->|"tool results"| RT_T
    RT_T -.->|"streaming response"| Browser_T

    RT_T -.->|"escalate → voice"| LiveKit_T[("LiveKit<br/>:7880")]
```

## Conditional Modes

| Mode | Config Key | Active Inference Services |
|------|-----------|--------------------------|
| `cascade` | `pipeline-type: cascade` | LLM + STT + TTS + Guardrails (all local GPU) |
| `cascade_remote` | `pipeline-type: cascade_remote` | Remote GPU port-forwards (LLM, STT, TTS, Guardrails from EKS) |
| `cascade_text` | `pipeline-type: cascade_text` | LLM + Guardrails only (no voice tier) |
| `openai` | `pipeline-type: openai` | OpenAI Realtime API (no local STT/TTS/LLM) |

## Data Shapes

| Boundary | Protocol | Data Format |
|----------|----------|-------------|
| Web → API | HTTP REST | JSON (sessions, accounts, feedback) |
| Web → Realtime-Text | WebSocket | JSON messages (client protocol) |
| Web → LiveKit | WebRTC | Opus audio frames + data channels |
| Realtime → API | HTTP Internal | JSON (tools, conversations) |
| Realtime → LLM | HTTP | OpenAI-compat chat completions (streaming) |
| Realtime → Guardrails | gRPC | Triton InferRequest (text tensor) |
| Realtime → STT | gRPC | Triton streaming InferRequest (audio PCM) |
| Realtime → TTS | gRPC | Triton InferRequest (text) → audio PCM |
| API → PostgreSQL | TCP | SQL via SQLAlchemy async |
| API → Redis | TCP | Redis protocol (sessions, rate limiting) |
| LiveKit → Redis | TCP | Redis protocol (room state) |

## Config Snapshot

| Parameter | Value | Source |
|-----------|-------|--------|
| LLM Model | google/gemma-4-26B-A4B-it | tilt_config / values.yaml |
| STT Model | nemotron_asr (NeMo 0.6B) | values.yaml |
| TTS Model | chatterbox_tts | values.yaml |
| LLM Guard | Nemotron-Content-Safety-4B | values.yaml |
| Pipeline Type | cascade (default) | tilt_config.json |
| System Prompt | gemma4_configurable (v8) | realtime-text config |
| STT Chunk | 80ms | values.yaml |
| VAD Confidence | 0.5 | cascade/pipeline.py |
| SmartTurn Stop | 1.5s | cascade/pipeline.py |
| Session TTL | 900s (15 min) | values.yaml |
| Rate Limit | 20 conn / 60s | values.yaml |
| Guardrails Threshold | 0.8 (prompt injection) | values.yaml |
| TTS Features | ACI + CUDA graphs + LoRA | values.yaml |
| Enabled Tools | visualise_data, capture_response | values.yaml |
