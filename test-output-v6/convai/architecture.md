# Concierge — Architecture

Financial conversational AI platform with text and voice interaction modes.

## Service Map Overview

```mermaid
flowchart TD
    subgraph Client
        Web["Web<br/>React + Vite :3000"]
    end

    subgraph Services
        API["API<br/>FastAPI :8000"]
        RT_Text["Realtime-Text<br/>FastAPI :8001 (WS)"]
        RT_Voice["Realtime-Voice<br/>LiveKit agent"]
        LiveKit["LiveKit<br/>SFU :7880"]
    end

    subgraph Inference
        LLM["LLM<br/>vLLM (Qwen3-8B)"]
        STT["STT<br/>Triton / Nemotron ASR"]
        TTS["TTS<br/>Triton / Chatterbox"]
        Guards["Guardrails<br/>Input / Output Rails"]
    end

    subgraph Infrastructure
        PG[("PostgreSQL :5432")]
        Redis[("Redis :6379")]
        RedisKV[("Redis KVCache")]
    end

    Web -->|REST /api| API
    Web -.->|WebSocket| RT_Text
    Web -.->|WS signal| LiveKit
    RT_Text -->|HTTP internal| API
    RT_Text -->|completions| LLM
    RT_Text ==>|input rails| Guards
    RT_Voice -->|voice comp| LLM
    RT_Voice ==>|gRPC audio| STT
    RT_Voice ==>|gRPC synth| TTS
    API -.-|queries| PG
    API -.-|sessions| Redis
    LLM -.-|KV cache| RedisKV
```

## Voice Pipeline (Cascade Mode)

```mermaid
flowchart LR
    LK_IN["LiveKit SFU"] -->|audio in| Receive
    subgraph Pipeline["Cascade Voice Pipeline"]
        direction TB
        Receive["Receive audio"] --> VAD["VAD (MarbleNet)"]
        VAD --> STT_Step["Speech-to-Text"]
        STT_Step --> LLM_Step["LLM completion"]
        LLM_Step --> TTS_Step["Text-to-Speech"]
        TTS_Step --> Send["Send audio"]
    end
    STT_Step -->|ASR stream| STT_Ext["STT (Triton)"]
    LLM_Step -->|HTTP /v1| LLM_Ext["LLM (vLLM)"]
    LLM_Step ==>|guard check| Guard_Ext["Guardrails"]
    TTS_Step -->|synth stream| TTS_Ext["TTS (Triton)"]
    Send -.->|audio out| LK_IN
```

## Data Shapes

| Shape | Source | Destination | Format |
|-------|--------|-------------|--------|
| Audio frames | LiveKit track | Realtime-Voice | PCM 16kHz |
| Transcript | STT (Triton) | LLM pipeline step | streaming text |
| Chat completion | vLLM | TTS pipeline step | SSE JSON chunks |
| Synthesised audio | TTS (Triton) | LiveKit publish | PCM frames |
| Chat messages | Web (WS) | Realtime-Text | JSON over WebSocket |
| Session state | API | Redis | key-value |
| User/account data | API | PostgreSQL | SQL (Alembic) |
| KV prefix cache | vLLM/LMCache | Redis KVCache | binary blobs |

## Config Snapshot

| Parameter | Value | Source |
|-----------|-------|--------|
| Pipeline type | `cascade` / `openai` | `tilt_config.json` |
| LLM model | `Qwen/Qwen3-8B-FP8` (default) | `tilt_config.json` |
| STT model | `nemotron_asr` | `tilt_config.json` |
| TTS model | `chatterbox_tts` / `kokoro_tts` | `tilt_config.json` |
| API port | 8000 | Helm values |
| Realtime-Text port | 8001 | Helm values |
| LiveKit ports | 7880 (signal), 7881 (RTC) | Helm values |
| Deploy target | Kubernetes (Kind / k3s local, EKS prod) | Tiltfile |
| Observability | Grafana + Tempo + Loki + Alloy (optional) | `tilt_config.json` |
