# Architecture

## Service Map

```mermaid
flowchart TD
    subgraph Client["Client Layer"]
        Web["Web Frontend<br/>React + Vite<br/>LiveKit JS SDK"]
    end

    subgraph Gateway["Gateway Layer"]
        API["API Service<br/>FastAPI · :8000<br/>Auth, Conversations, Tools"]
    end

    subgraph Services["Application Services"]
        RT_Text["Realtime-Text<br/>:8001 · WebSocket<br/>Chat pipeline + GuardService"]
        LiveKit["LiveKit<br/>:7880 · WebRTC SFU<br/>Room management"]
        RT_Voice["Realtime-Voice<br/>LiveKit agent<br/>Cascade: STT→LLM→TTS"]
    end

    subgraph Infra["Infrastructure"]
        Postgres[("PostgreSQL<br/>:5432")]
        Redis[("Redis<br/>:6379 · sessions")]
        LLM["LLM (vLLM)<br/>gemma-4-26B-A4B-it<br/>OpenAI-compat API"]
        Guardrails["Guardrails (Triton)<br/>:8001 gRPC<br/>injection + multi + PII"]
        LLM_Guard["LLM-Guard (vLLM)<br/>Nemotron-4B<br/>Content safety"]
        STT["STT (Triton)<br/>nemotron_asr<br/>Streaming ASR"]
        TTS["TTS (Triton)<br/>chatterbox_tts<br/>Neural synthesis"]
    end

    Web -->|"REST /api"| API
    Web -.->|"WebSocket"| RT_Text
    Web -.->|"WebRTC"| LiveKit

    API -->|"queries"| Postgres
    API -.->|"sessions"| Redis

    RT_Text -->|"tools"| API
    RT_Text -->|"completions"| LLM
    RT_Text -->|"gRPC guards"| Guardrails
    RT_Text -->|"safety"| LLM_Guard
    RT_Text <-.->|"rooms"| LiveKit

    RT_Voice -->|"tools"| API
    RT_Voice -->|"completions"| LLM
    RT_Voice -->|"gRPC guards"| Guardrails
    RT_Voice -->|"safety"| LLM_Guard
    RT_Voice -->|"audio"| STT
    RT_Voice -->|"text"| TTS
    RT_Voice <-.->|"audio frames"| LiveKit

    LiveKit -.->|"rooms"| Redis
```

### Cascade vs OpenAI Pipeline Modes

```mermaid
flowchart LR
    subgraph Cascade["mode: cascade"]
        direction LR
        C_STT["STT<br/>nemotron_asr"] --> C_LLM["LLM<br/>gemma-4-26B"]
        C_LLM --> C_TTS["TTS<br/>chatterbox"]
    end

    subgraph OpenAI["mode: openai"]
        direction LR
        O_RT["OpenAI Realtime API<br/>gpt-realtime<br/>voice: shimmer"]
    end

    Voice_Worker["Realtime-Voice"] -->|"PIPELINE_TYPE=cascade"| Cascade
    Voice_Worker -->|"PIPELINE_TYPE=openai"| OpenAI
```

### Guardrails Pipeline

```mermaid
flowchart TD
    subgraph Guard_Cascade["Guard Cascade (per message)"]
        Greeting["GreetingDetector<br/>in-process regex"]
        Lang["language_guard<br/>fastText · CPU"]
        PI["prompt_injection<br/>DeBERTa ONNX · GPU"]
        Multi["multi_guard<br/>SentenceTransformer · GPU"]
        LLM_G["LLM Guard<br/>Nemotron-4B"]
        PII["pii_guard<br/>GLiNER + regex · GPU"]
    end

    Input["User message"] --> Greeting
    Greeting -->|"not greeting"| Lang
    Lang & PI & Multi -->|"parallel"| Resolve["_resolve_safety"]
    Resolve -->|"uncertain"| LLM_G
    Resolve -->|"safe"| PII
    PII --> Output["Sanitised text → LLM"]
```

## Data Shapes

| Boundary | Protocol | Data Format |
|---|---|---|
| Web → API | HTTP REST | JSON (sessions, conversations, feedback) |
| Web → Realtime-Text | WebSocket | JSON frames (chat messages, components) |
| Web ↔ LiveKit | WebRTC | Audio/video tracks via SFU |
| Realtime → API | HTTP internal | JSON (tool calls: transactions, cash-flow) |
| Realtime → LLM | HTTP | OpenAI-compat chat completions (streaming) |
| Realtime → Guardrails | gRPC (Triton) | text tensors → bool + confidence |
| Realtime → LLM-Guard | HTTP | OpenAI-compat chat (safety classification) |
| Realtime-Voice → STT | gRPC (Triton) | audio chunks → transcription text |
| Realtime-Voice → TTS | gRPC (Triton) | text → audio PCM |
| LiveKit → Redis | pub/sub | Room state, participant events |
| API → PostgreSQL | SQL (asyncpg) | Conversations, accounts, profiles |
| API → Redis | Redis protocol | Session tokens, rate limits, import state |

## Config Snapshot

| Parameter | Value |
|---|---|
| LLM model | google/gemma-4-26B-A4B-it |
| LLM-Guard model | nvidia/Nemotron-Content-Safety-Reasoning-4B |
| STT model | nemotron_asr |
| TTS model | chatterbox_tts |
| TTS voice (kokoro) | af_heart |
| Pipeline modes | cascade, openai |
| System prompt version | gemma4_configurable (v8) |
| Enabled tools | visualise_data, capture_response |
| VAD confidence | 0.5 |
| VAD start/stop | 0.2s / 0.7s |
| SmartTurn stop | 1.5s |
| Session TTL | 900s |
| Connection rate limit | 20/60s |
| Guardrails threshold | 0.8 (prompt injection) |
| Database | PostgreSQL :5432 |
| Cache | Redis :6379 |
| LiveKit signal port | 7880 |
| Web frontend | React + Vite :3000 |
| API port | 8000 |
| Cluster options | kind, k3s |
