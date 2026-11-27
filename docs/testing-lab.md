# End-to-End Testing Lab & AI Client Simulator

## Overview

The **Testing Lab** (`/testing-lab`) validates agentVoice end-to-end across AI conversation quality, voice-to-voice roundtrips, Knowledge Base RAG accuracy, compliance rules, telephony dry-run/authorized test calls, local concurrency benchmarks, and failure recovery.

## Test Modes & Integrity

Every test run is explicitly labeled with its execution mode (`mocked`, `local_simulation`, `real_microphone`, `real_telephony`). Mocked or simulated tests are never presented as verified real-world telephone calls.

## Components

- **AI Client Simulator (`apps/api/app/services/testing_simulator.py`)**: Includes 15 built-in customer personas (Interested, Confused, Busy, Price-Sensitive, Skeptical, Angry, Uninterested, Technical, Hindi, Hinglish, Interrupting, Silent, Unclear Audio, Callback, Human Handoff) plus custom persona creation.
- **Deterministic Conversation Evaluator (`ConversationEvaluator`)**: Scores 14 criteria (0–100) and enforces deterministic critical compliance assertions (opt-out respect, no unauthorized discount invention, AI identity disclosure, non-empty responses).
- **Autonomous Testing Assistant (`TestingAssistantService`)**: Inspects agent config, Ollama, STT/TTS, KB, and Telephony readiness; warns about missing dependencies; and executes authorized local simulations.
- **Specialized Suites (`apps/api/app/services/testing_suites.py`)**: Knowledge Base & prompt-injection isolation tests, Telephony dry-run & consent-gated real test-call checks, local concurrency benchmarks, and failure-recovery checks.
