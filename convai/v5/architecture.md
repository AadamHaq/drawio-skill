# Architecture — Concierge (ConvAI)

Financial conversational AI platform with real-time voice and text interactions, supporting multiple pipeline modes (cascade with local inference, or OpenAI Realtime).

### Service Map

```mermaid
flowchart TD
    subgraph Client["Client Layer"]
        Web["Web Frontend<br/>React / Vite :3000<br/>LiveKit JS SDK · Faro"]
    end

    subgraph Gateway["Gateway Layer"]
        API["API Service<br/>FastAPI :8000<br/>Auth · BoA · Conversations"]
    end

    subgraph Services["Service Layer"]
        RT_Text["Realtime-Text<br/>FastAPI :8001<br/>WebSocket Chat · Voice Escalation"]
        LiveKit["LiveKit<br/>WebRTC SFU :7880<br/>Media :7881 · Room Mgmt"]
    end

    subgraph Workers["Worker Layer"]
        RT_Voice["Realtime-Voice<br/>Pipecat Pipeline<br/>VAD · SmartTurn · Tools"]
    end

    subgraph Inference["Inference Layer (cascade mode)"]
        LLM["LLM (vLLM)<br/>gemma-4-26B-A4B-it<br/>OpenAI-compat + LMCache"]
        STT["STT (Triton)<br/>nemotron_asr<br/>gRPC :9101"]
        TTS["TTS (Triton)<br/>chatterbox_tts<br/>gRPC :9201"]
        Guards["Guardrails (Triton)<br/>prompt_injection · multi_guard<br/>language · PII"]
    end

    subgraph Infra["Infrastructure"]
        PG[("PostgreSQL :5432")]
        Redis[("Redis :6379")]
        RedisKV[("Redis KVCache :6379")]
    end

    %% Client connections
    Web -->|"REST /api"| API
    Web -.->|"WebSocket"| RT_Text
    Web -.->|"WebRTC"| LiveKit

    %% Gateway connections
    API -->|"queries"| PG
    API -->|"sessions"| Redis

    %% Service connections
    RT_Text -->|"persist"| API
    RT_Text -.->|"escalation"| LiveKit
    RT_Text -->|"completions"| LLM
    RT_Text -->|"text check"| Guards

    %% Worker connections
    RT_Voice <-.->|"audio"| LiveKit
    RT_Voice -->|"persist"| API
    RT_Voice -->|"completions"| LLM
    RT_Voice -->|"audio chunks"| STT
    RT_Voice -->|"text segments"| TTS
    RT_Voice -->|"text check"| Guards

    %% Infrastructure connections
    LiveKit -.->|"room state"| Redis
    LLM -.->|"KV tensors"| RedisKV
```

### Voice Cascade Pipeline

```mermaid
flowchart TD
    Browser["Browser<br/>LiveKit JS SDK"]
    LK["LiveKit SFU<br/>WebRTC :7880 · RTC :7881"]

    subgraph Worker["Realtime-Voice Worker (Pipecat)"]
        VAD["Voice Activity Detection<br/>MarbleNet · conf: 0.5<br/>start: 0.2s · stop: 0.7s"]
        SmartTurn["SmartTurn v3<br/>stop_secs: 1.5 · timeout: 2.0s"]
        STT_Step["Speech-to-Text<br/>nemotron_asr (Triton gRPC)<br/>chunk: 80ms · preroll: 300ms"]
        GuardIn["Input Guardrails<br/>prompt_injection · language · PII"]
        LLM_Step["LLM Inference<br/>vLLM · gemma-4-26B-A4B-it<br/>streaming OpenAI-compat"]
        GuardOut["Output Guardrails<br/>toxicity · advisory · off-topic"]
        TTS_Step["Text-to-Speech<br/>chatterbox_tts (Triton gRPC)<br/>streaming audio chunks"]
    end

    API_Svc["API Service<br/>conversation persistence"]

    Browser <-.->|"WebRTC audio"| LK
    LK -.->|"audio frames"| VAD
    VAD --> SmartTurn
    SmartTurn --> STT_Step
    STT_Step --> GuardIn
    GuardIn --> LLM_Step
    LLM_Step --> GuardOut
    GuardOut --> TTS_Step
    TTS_Step -.->|"audio out"| LK
    Worker -->|"persist turn"| API_Svc
```

### OpenAI Realtime Mode

```mermaid
flowchart TD
    Browser2["Browser<br/>LiveKit JS SDK"]
    LK2["LiveKit SFU"]

    subgraph Worker2["Realtime-Voice Worker (OpenAI mode)"]
        Transport2["LiveKit Transport<br/>audio in/out"]
        OAI["OpenAI Realtime LLM<br/>gpt-realtime · voice: shimmer"]
        Tools2["Tool Executor<br/>function calling"]
        Keepalive["Keepalive Processor"]
    end

    OpenAI_Cloud["OpenAI API (external)"]

    Browser2 <-.->|"WebRTC"| LK2
    LK2 <-.->|"audio"| Transport2
    Transport2 --> OAI
    OAI -->|"fn calls"| Tools2
    OAI -->|"heartbeat"| Keepalive
    OAI -->|"realtime API"| OpenAI_Cloud
```

## Data Shapes

| Boundary | Input | Output |
|----------|-------|--------|
| Browser → API | HTTP REST (JSON) | Session tokens, conversation state |
| Browser → Realtime-Text | WebSocket frames (JSON) | Chat messages, tool results |
| Browser → LiveKit | WebRTC audio (PCM 16kHz) | WebRTC audio (PCM 24kHz) |
| Realtime-Voice → STT | gRPC: audio chunks (80ms) | Transcription text |
| Realtime-Voice → LLM | HTTP: OpenAI chat completion | Streaming token chunks |
| Realtime-Voice → TTS | gRPC: text segments | Audio PCM chunks |
| Realtime → Guardrails | gRPC: text string | is_safe, confidence, redacted_text |
| API → PostgreSQL | SQL (SQLAlchemy async) | Conversations, users, accounts |
| API → Redis | Key-value (sessions, rate limits) | Session data |
| LLM → Redis KVCache | KV cache tensors (LMCache) | Cached KV state |

## Config Snapshot

| Parameter | Value | Source |
|-----------|-------|--------|
| pipeline-type | cascade (default) | tilt_config.json |
| llm-model | google/gemma-4-26B-A4B-it | tilt_config.json |
| stt-model | nemotron_asr | tilt_config.json |
| tts-model | chatterbox_tts | tilt_config.json |
| tts-voice (kokoro) | af_heart | Tiltfile |
| vad_confidence | 0.5 | cascade/pipeline.py |
| vad_start_secs | 0.2 | cascade/pipeline.py |
| vad_stop_secs | 0.7 | cascade/pipeline.py |
| smart_turn_stop_secs | 1.5 | cascade/pipeline.py |
| stt_chunk_ms | 80 | registries.py |
| stt_preroll_ms | 300 | registries.py |
| voice_join_timeout | 15.0s | config.py |
| voice_reconnect_grace | 5.0s | config.py |
| prompt_injection_threshold | 0.8 | guardrails README |

## Service Summary

| Service | Path | Runtime | Port | Protocol |
|---------|------|---------|------|----------|
| Web | services/web | always-running | 3000 | HTTP |
| API | services/api | always-running | 8000 | HTTP |
| Realtime-Text | services/realtime (tier=text) | always-running | 8001 | HTTP + WS |
| Realtime-Voice | services/realtime (tier=voice) | always-running | 8000 | HTTP + WS |
| LLM (vLLM) | services/llm | always-running | 8000 | HTTP |
| STT (Triton) | services/stt | always-running | 9101 | gRPC |
| TTS (Triton) | services/tts | always-running | 9201 | gRPC |
| Guardrails (Triton) | services/guardrails | always-running | 9021 | gRPC |
| LiveKit | deploy/charts (3rd party) | always-running | 7880/7881 | WS + RTC |
| PostgreSQL | infrastructure | always-running | 5432 | TCP |
| Redis | infrastructure | always-running | 6379 | TCP |
| Redis KVCache | infrastructure | always-running | 6379 | TCP |
