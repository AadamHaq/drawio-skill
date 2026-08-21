# Concierge Architecture

Financial conversational AI platform with text and voice modes.

## Overview

```mermaid
flowchart TD
    subgraph Client
        Web["Web<br/>React + Vite :3000"]
    end

    subgraph Platform
        API["API<br/>FastAPI :8000"]
        LiveKit["LiveKit<br/>WebRTC SFU :7880"]
    end

    subgraph Services
        RT_Text["Realtime-Text<br/>WebSocket Chat"]
        RT_Voice["Realtime-Voice<br/>Pipecat Pipeline"]
    end

    subgraph Inference
        LLM["LLM<br/>vLLM (OpenAI-compat)"]
        Guardrails["Guardrails<br/>Triton :9021"]
        STT["STT<br/>Triton NeMo ASR"]
        TTS["TTS<br/>Triton Chatterbox"]
    end

    subgraph Infrastructure
        Postgres["PostgreSQL :5432"]
        Redis["Redis :6379"]
        RedisKV["Redis KVCache"]
    end

    Web -->|REST /api| API
    Web -.->|WebSocket| RT_Text
    Web -.->|WebRTC| LiveKit
    LiveKit -.->|audio relay| RT_Voice
    RT_Text -->|internal API| API
    RT_Text -->|completions| LLM
    RT_Text ==>|text guard| Guardrails
    RT_Voice -->|voice comp| LLM
    RT_Voice ==>|gRPC audio| STT
    RT_Voice ==>|gRPC synth| TTS
    API -.->|queries| Postgres
    API -.->|sessions| Redis
```

## Voice Pipeline (Cascade Mode)

```mermaid
flowchart TD
    LK["LiveKit SFU"] -.->|audio in| VAD

    subgraph Pipeline["Realtime-Voice (Pipecat)"]
        VAD["VAD<br/>MarbleNet ONNX"]
        STT_Step["STT<br/>Nemotron streaming"]
        Norm["Normalise<br/>ASR text"]
        LLM_Step["LLM<br/>Qwen3-8B streaming"]
        Agg["Aggregate<br/>Bounded text + tools"]
        TTS_Step["TTS<br/>Chatterbox synthesis"]

        VAD --> STT_Step --> Norm --> LLM_Step --> Agg --> TTS_Step
    end

    STT_Step ==>|gRPC stream| STT_Svc["STT Triton :9101"]
    LLM_Step -->|HTTP /v1| LLM_Svc["LLM vLLM :9000"]
    LLM_Step ==>|guard check| Guard["Guardrails :9021"]
    Agg -->|tool calls| API_Svc["API Service"]
    TTS_Step ==>|gRPC infer| TTS_Svc["TTS Triton :9201"]
```

## Data Shapes

| Shape | Source | Format | Description |
|-------|--------|--------|-------------|
| Audio frames | LiveKit | PCM 16kHz | Raw audio from WebRTC |
| Transcript | STT | Streaming text | Partial/final ASR output |
| Chat messages | LLM | OpenAI-compat JSON | Streamed completion deltas |
| Guard verdict | Guardrails | gRPC response | is_safe, confidence, redacted_text |
| Synthesised audio | TTS | PCM chunks | Audio frames for playback |
| Tool results | API | JSON | Bank accounts, transactions |

## Config Snapshot

| Key | Default | Description |
|-----|---------|-------------|
| pipeline-type | `cascade` | Inference pipeline mode (cascade, openai, cascade_remote) |
| llm-model | `google/gemma-4-26B-A4B-it` | LLM model served by vLLM |
| stt-model | `nemotron_asr` | Triton STT model name |
| tts-model | `chatterbox_tts` | Triton TTS model name (alt: kokoro_tts) |
| guardrails | `false` | Enable Triton guardrails service |
| VAD confidence | `0.5` | MarbleNet voice activity threshold |
| VAD start | `0.15s` | Speech start detection window |
| VAD stop | `0.7s` | Speech end detection window |
| VAD min volume | `0.25` | Minimum volume for VAD trigger |

## Services

| Service | Port | Framework | Role |
|---------|------|-----------|------|
| Web | 3000 | React + Vite | Browser SPA with LiveKit JS SDK |
| API | 8000 | FastAPI | REST API, auth, sessions, BoA banking, conversations |
| Realtime-Text | 8001 | FastAPI (WS) | Text chat tier with guardrails orchestration |
| Realtime-Voice | 8000 | FastAPI + Pipecat | Voice cascade: VAD → STT → LLM → TTS |
| LiveKit | 7880 | LiveKit Server | WebRTC SFU for media relay and room management |
| LLM | 9000 | vLLM + LMCache | OpenAI-compatible inference with KV cache |
| STT | 9101 | Triton (gRPC) | NeMo ASR (Nemotron/Parakeet) |
| TTS | 9201 | Triton (gRPC) | Chatterbox / Kokoro speech synthesis |
| Guardrails | 9021 | Triton (gRPC) | 4 models: prompt_injection, multi_guard, language_guard, pii_guard |
| PostgreSQL | 5432 | PostgreSQL 16 | Conversations, user profiles, accounts |
| Redis | 6379 | Redis 7 | Sessions, rate limiting, feature flags |
| Redis KVCache | 6379 | Redis 7 | LMCache prefix KV store |
