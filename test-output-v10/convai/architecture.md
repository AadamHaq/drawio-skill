# Concierge Architecture

Financial conversational AI platform with real-time voice and text interactions.

## Overview (Service Map)

```mermaid
graph TD
    subgraph Client
        Web["Web<br/>React 18 / Vite :3000"]
    end

    subgraph Services
        API["API<br/>FastAPI :8000"]
        RT_Text["Realtime-Text<br/>FastAPI WS :8001"]
        RT_Voice["Realtime-Voice<br/>Pipecat Pipeline"]
        LiveKit["LiveKit<br/>WebRTC SFU :7880"]
    end

    subgraph Inference
        LLM["LLM<br/>vLLM (Gemma4/Qwen3)"]
        STT["STT<br/>Triton (Nemotron ASR)"]
        TTS["TTS<br/>Triton (Chatterbox)"]
        Guardrails["Guardrails<br/>Triton Multi-Guard"]
    end

    subgraph Infrastructure
        Postgres[("PostgreSQL 16<br/>users, conversations")]
        Redis[("Redis 7<br/>sessions, pub/sub")]
    end

    Web -->|REST /api| API
    Web -.->|WebSocket| RT_Text
    Web -.->|WebRTC| LiveKit
    API -.->|queries| Postgres
    API -.->|sessions| Redis
    RT_Text -->|text comp| LLM
    RT_Voice -->|voice comp| LLM
    RT_Voice ==>|gRPC audio| STT
    RT_Voice ==>|gRPC synth| TTS
    RT_Voice -->|room join| LiveKit
    RT_Text ==>|guard check| Guardrails
    LiveKit -.->|pub/sub| Redis
```

## Voice Pipeline (Data Flow)

```mermaid
graph TD
    subgraph CascadePipeline["Cascade Voice Pipeline"]
        A1["Audio In (LiveKit)<br/>transport.input() 16kHz PCM"]
        A2["VAD (MarbleNet)<br/>conf=0.5, start=150ms, stop=700ms"]
        A3["STT (Nemotron ASR)<br/>chunk=80ms, preroll=300ms"]
        A4["LLM (vLLM / Gemma4)<br/>streaming, tool-calling"]
        A5["TTS (Chatterbox)<br/>bounded text agg, NL split"]
        A6["Audio Out (LiveKit)<br/>transport.output() + audit"]
        A1 --> A2 --> A3 --> A4 --> A5 --> A6
    end

    LK["LiveKit SFU<br/>WebRTC :7880"] -.->|audio in| A1
    A3 ==>|gRPC ASR| TritonSTT["Triton STT<br/>gRPC :9101"]
    A4 -->|HTTP /v1| vLLM["vLLM Server<br/>HTTP :9000/v1"]
    A5 ==>|gRPC TTS| TritonTTS["Triton TTS<br/>gRPC :9201"]
    Guard["Guardrails<br/>gRPC :9301"] ==>|rail check| A4
    A6 -.->|audio out| LK
```

## Data Shapes

| Service | Input | Output | Protocol |
|---------|-------|--------|----------|
| Web | User interaction | REST requests, WebSocket messages | HTTP, WS |
| API | HTTP requests | JSON responses, DB writes | REST |
| Realtime-Text | WebSocket text | LLM completions, tool results | WS, HTTP |
| Realtime-Voice | Audio frames (16kHz PCM) | Audio frames (TTS output) | WebRTC, gRPC |
| LiveKit | WebRTC signalling | Room events, audio relay | WebSocket, RTP |
| LLM (vLLM) | OpenAI-format messages | Streaming token completions | HTTP /v1 |
| STT (Triton) | Audio chunks (80ms) | Text transcriptions | gRPC |
| TTS (Triton) | Text segments | Audio PCM frames | gRPC |
| Guardrails | User/assistant text | Pass/block decision | gRPC |
| PostgreSQL | SQL queries | Row sets | TCP :5432 |
| Redis | Key/channel ops | Values, pub/sub messages | TCP :6379 |

## Config Snapshot

| Parameter | Value | Source |
|-----------|-------|--------|
| Pipeline type | `cascade` / `openai` | `tilt_config.json` |
| LLM model | `google/gemma-4-26B-A4B-it` | `tilt_config.json` |
| STT model | `nemotron_asr` | Triton model_repository |
| TTS model | `chatterbox_tts` | Triton model_repository |
| TTS fallback | `kokoro_tts` (voice: `af_heart`) | `tilt_config.json` |
| VAD confidence | 0.5 | `cascade/pipeline.py` |
| VAD start | 150ms | `cascade/pipeline.py` |
| VAD stop | 700ms | `cascade/pipeline.py` |
| SmartTurn stop | 1.5s | `cascade/pipeline.py` |
| STT chunk | 80ms | env `STT_CHUNK_MS` |
| STT preroll | 300ms | env `STT_PREROLL_MS` |
| API port | 8000 | Uvicorn config |
| Realtime-Text port | 8001 (host) / 8000 (container) | Helm values |
| LiveKit port | 7880 (signal) / 7881 (RTC) | Helm values |
| Redis | 7-alpine :6379 | `deploy/envs/local/redis.yaml` |
| PostgreSQL | 16-alpine :5432 | `deploy/envs/local/postgres.yaml` |
| Kubernetes | Kind (macOS) / k3s (Linux) | `tilt_config.json` |
| Deployment | Tilt + Helm charts | `Tiltfile` |
