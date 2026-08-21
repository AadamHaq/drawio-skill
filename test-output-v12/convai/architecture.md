# Concierge Architecture

Financial conversational AI platform with text and voice modes.

## Service Map (Overview)

```mermaid
flowchart TD
    subgraph Client
        Web["Web<br/>React + Vite :3000"]
    end

    subgraph Gateway
        API["API<br/>FastAPI :8000"]
    end

    subgraph Services
        RT-Text["RT-Text<br/>FastAPI :8001"]
        RT-Voice["RT-Voice<br/>FastAPI :8002"]
        LiveKit["LiveKit<br/>livekit-server :7880"]
    end

    subgraph Inference
        LLM["LLM<br/>vLLM (Qwen3/Gemma-4)"]
        STT["STT<br/>Triton (Nemotron ASR)"]
        TTS["TTS<br/>Triton (Chatterbox/Kokoro)"]
        Guardrails["Guardrails<br/>Triton (Input/Output rails)"]
    end

    subgraph Infrastructure
        PostgreSQL[("PostgreSQL v16<br/>Conversations")]
        Redis[("Redis v7<br/>Sessions + Rooms")]
    end

    Web -->|REST /api| API
    Web -.->|WebSocket| RT-Text
    Web -.->|WebRTC| LiveKit
    API -->|HTTP internal| RT-Text
    API -.->|queries| PostgreSQL
    API -.->|sessions| Redis
    RT-Text -->|text comp| LLM
    RT-Text ==>|guard check| Guardrails
    RT-Voice -->|voice comp| LLM
    RT-Voice ==>|gRPC audio| STT
    RT-Voice ==>|gRPC synth| TTS
    LiveKit -.->|room state| Redis
```

## Voice Pipeline (Data Flow)

```mermaid
flowchart TD
    subgraph VoicePipeline["Voice Pipeline (Cascade · Pipecat)"]
        A["Audio In<br/>LiveKit transport"] --> B["VAD<br/>MarbleNet (conf 0.5)"]
        B --> C["STT Transcribe<br/>Nemotron ASR gRPC"]
        C --> D["Smart Turn Detect<br/>LocalSmartTurnV3 1.5s"]
        D --> E["LLM Generate<br/>vLLM streaming"]
        E --> F["TTS Synthesise<br/>Chatterbox gRPC"]
        F --> G["Audio Out<br/>LiveKit transport"]
    end

    LK["LiveKit<br/>WebRTC SFU :7880"] -->|audio in| A
    G -.->|audio out| LK
    C ==>|gRPC audio| STTx["STT<br/>Triton (Nemotron)"]
    E -->|completions| LLMx["LLM<br/>vLLM (Qwen/Gemma)"]
    F ==>|gRPC synth| TTSx["TTS<br/>Triton (Chatterbox)"]
```

## Data Shapes

| Service | Interface | Protocol | Port |
|---------|-----------|----------|------|
| Web | Vite dev / nginx | HTTP | 3000 |
| API | FastAPI (REST) | HTTP | 8000 |
| RT-Text | FastAPI (WebSocket) | WS | 8001 |
| RT-Voice | FastAPI (Pipecat) | Internal | 8002 |
| LiveKit | livekit-server (WebRTC SFU) | WS/RTC | 7880 |
| LLM | vLLM (OpenAI-compatible API) | HTTP | 9000 |
| STT | Triton Inference Server | gRPC | 9101 |
| TTS | Triton Inference Server | gRPC | 9201 |
| Guardrails | Triton Inference Server | gRPC | 9301 |
| PostgreSQL | postgres:16-alpine | TCP | 5432 |
| Redis | redis:7-alpine | TCP | 6379 |

## Config Snapshot

| Parameter | Value | Source |
|-----------|-------|--------|
| Pipeline type | `cascade` / `openai` | `tilt_config.json` |
| LLM model | `Qwen/Qwen3-8B-FP8` or `google/gemma-4-26B-A4B-it` | `tilt_config.json` |
| STT model | `nemotron_asr` | `tilt_config.json` |
| TTS model | `chatterbox_tts` / `kokoro_tts` | `tilt_config.json` |
| VAD confidence | 0.5 | `pipeline/cascade/pipeline.py` |
| VAD start | 0.15s | `pipeline/cascade/pipeline.py` |
| VAD stop | 0.7s | `pipeline/cascade/pipeline.py` |
| Smart turn timeout | 1.5s | `pipeline/cascade/pipeline.py` |
| Voice join timeout | 15s | `app/config.py` |
| Voice reconnect grace | 5s | `app/config.py` |
| Cluster | Kind (macOS) / k3s (Linux) | `tilt_config.json` |
| Auth | Staff SSO / LaunchDarkly flags | `shared/auth/` |
