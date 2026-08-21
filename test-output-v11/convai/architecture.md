# Concierge — Architecture

Financial conversational AI platform with text and voice modes, deployed on Kubernetes (Kind/k3s locally, EKS in production).

## Overview

```mermaid
flowchart TD
    subgraph Client
        Web["Web<br/>React + Vite :3000"]
    end

    subgraph Services
        API["API<br/>FastAPI :8000"]
        RT_Text["Realtime-Text<br/>text tier worker"]
        RT_Voice["Realtime-Voice<br/>voice tier worker"]
    end

    subgraph Platform
        LiveKit["LiveKit<br/>WebRTC SFU :7880"]
    end

    subgraph Inference
        LLM["LLM<br/>vLLM (OpenAI API)"]
        STT["STT<br/>Triton Nemotron :9101"]
        TTS["TTS<br/>Triton Chatterbox :9201"]
        Guardrails["Guardrails<br/>Triton :9301"]
    end

    subgraph Infrastructure
        PostgreSQL["PostgreSQL<br/>postgres:16-alpine"]
        Redis["Redis<br/>redis:7-alpine"]
    end

    Web -->|REST /api| API
    Web -.->|WebSocket| RT_Text
    RT_Text -->|escalation| RT_Voice
    RT_Text -->|room create| LiveKit
    RT_Voice -.->|audio I/O| LiveKit
    RT_Text -->|text comp| LLM
    RT_Voice -->|voice comp| LLM
    RT_Voice ==>|gRPC audio| STT
    RT_Voice ==>|gRPC synth| TTS
    API -.->|queries| PostgreSQL
    API -.->|sessions| Redis
    LiveKit -.->|pub/sub| Redis
```

## Voice Pipeline (Cascade)

```mermaid
flowchart TD
    LK_In["LiveKit (WebRTC)"] -.->|WebRTC audio| AudioIn

    subgraph CascadePipeline["Cascade Voice Pipeline (Pipecat)"]
        AudioIn["Audio In<br/>LiveKit transport frames"]
        VAD["VAD<br/>MarbleNet 0.5 conf / 0.7s stop"]
        STT_Step["Speech-to-Text<br/>Nemotron ASR streaming"]
        LLM_Step["LLM Completion<br/>vLLM OpenAI /v1"]
        TTS_Step["Text-to-Speech<br/>Chatterbox / Kokoro"]
        AudioOut["Audio Out<br/>PCM → LiveKit transport"]

        AudioIn --> VAD --> STT_Step --> LLM_Step --> TTS_Step --> AudioOut
    end

    STT_Step ==>|gRPC stream| STT_Svc["STT Service<br/>Triton :9101"]
    LLM_Step -->|HTTP /v1| LLM_Svc["LLM Service<br/>vLLM Gemma-4 / Qwen3"]
    TTS_Step ==>|gRPC synth| TTS_Svc["TTS Service<br/>Triton :9201"]

    AudioOut -.->|audio out| LK_In
```

## Data Shapes

| Boundary | Protocol | Format | Notes |
|----------|----------|--------|-------|
| Web → API | HTTP REST | JSON | `/api/v1/*` endpoints |
| Web → RT-Text | WebSocket | JSON frames | Chat messages, voice escalation signals |
| RT-Text → RT-Voice | HTTP | Internal API | Voice session creation via LiveKit |
| RT-Voice ↔ LiveKit | WebSocket | WebRTC | Audio frames (PCM), signalling |
| RT-Voice → STT | gRPC | Streaming audio | Triton Nemotron ASR model |
| RT-Voice → LLM | HTTP | OpenAI-compat JSON | `/v1/chat/completions` (streaming) |
| RT-Voice → TTS | gRPC | Text → audio | Triton Chatterbox/Kokoro model |
| RT-* → Guardrails | gRPC | Text | Input/output safety rails |
| API → PostgreSQL | TCP | SQL (asyncpg) | Sessions, conversations, accounts |
| API → Redis | TCP | Redis protocol | Session cache, rate limiting |
| LiveKit → Redis | TCP | Redis pub/sub | Room state coordination |

## Config Snapshot

| Key | Default | Source |
|-----|---------|--------|
| `pipeline-type` | `cascade` | `tilt_config.json` |
| `llm-model` | `google/gemma-4-26B-A4B-it` | `tilt_config.json` |
| `stt-model` | `nemotron_asr` | `tilt_config.json` |
| `tts-model` | `chatterbox_tts` | `tilt_config.json` |
| VAD confidence | 0.5 | `pipeline/cascade/pipeline.py` |
| VAD stop secs | 0.7s | `pipeline/cascade/pipeline.py` |
| SmartTurn stop | 1.5s | `pipeline/cascade/pipeline.py` |
| VAD min volume | 0.25 | `pipeline/cascade/pipeline.py` |
| LiveKit SFU port | 7880 | Helm chart |
| LiveKit RTC port | 7881 | Helm chart |
| API port | 8000 | Dockerfile |
| RT-Text port | 8001 | Tilt config |
