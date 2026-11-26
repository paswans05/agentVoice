"""Tests for PromptBuilder, ConversationService, and streaming chat endpoints."""

from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.api.v1.llm import get_llm_provider
from app.core.config import Settings, get_settings
from app.main import create_app
from app.providers.llm import LLMGenerationConfig, LLMProvider
from app.schemas.agent import Agent, ModelConfig
from app.schemas.llm import ChatMessage, LLMModelInfo, LLMRuntimeHealth, ModelStatus
from app.services.prompt_builder import PromptBuilder


class FakeChatProvider(LLMProvider):
    """Deterministic fake LLMProvider for testing conversations and streaming."""

    provider_id = "ollama"

    def __init__(self, *, fail_mid_stream: bool = False) -> None:
        self.fail_mid_stream = fail_mid_stream
        self.last_messages: list[dict[str, str]] = []
        self.installed = ["qwen2.5:3b"]

    async def health_check(self) -> LLMRuntimeHealth:
        return LLMRuntimeHealth(provider="ollama", available=True, endpoint="http://localhost:11434")

    async def list_models(self) -> list[LLMModelInfo]:
        return [LLMModelInfo(id=m, name=m, status=ModelStatus.INSTALLED) for m in self.installed]

    async def has_model(self, model_id: str) -> bool:
        return model_id in self.installed

    async def generate(self, messages: list[dict[str, str]], config: LLMGenerationConfig) -> str:
        self.last_messages = messages
        return "Namaste! Main aapki help kar sakti hoon."

    async def stream(
        self, messages: list[dict[str, str]], config: LLMGenerationConfig
    ) -> AsyncIterator[str]:
        self.last_messages = messages
        yield "Namaste! "
        if self.fail_mid_stream:
            raise RuntimeError("Simulated stream interruption")
        yield "Kaise madad karun?"

    async def pull_model(self, model_id: str) -> AsyncIterator[dict[str, Any]]:
        yield {"status": "success"}

    async def delete_model(self, model_id: str) -> None:
        pass


def _make_client(tmp_path: Path, provider: LLMProvider) -> TestClient:
    app = create_app()
    test_settings = Settings(app_env="test", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return TestClient(app)


def _create_agent(client: TestClient, model_id: str = "qwen2.5:3b") -> dict:
    payload = {
        "name": "Asha Hindi Agent",
        "description": "Tests local Hindi/Hinglish conversations",
        "type": "SALES",
        "instructions": {
            "system_prompt": "Be polite and helpful.",
            "greeting": "Namaste!",
            "additional_rules": ["Never invent prices."],
        },
        "language": {
            "primary_language": "hi-IN",
            "supported_languages": ["hi-IN", "en-IN"],
            "hinglish_enabled": True,
            "response_mode": "AUTO",
        },
        "model": {
            "provider": "ollama",
            "model_id": model_id,
            "temperature": 0.5,
            "max_tokens": 256,
            "context_window_messages": 4,
        },
    }
    resp = client.post("/api/v1/agents", json=payload)
    assert resp.status_code == 201
    return resp.json()["data"]


def test_prompt_builder_respects_context_window() -> None:
    agent = Agent(
        id="agent_test01",
        name="Asha",
        model=ModelConfig(model_id="qwen2.5:3b", context_window_messages=2),
    )
    history = [
        ChatMessage(role="user", content="msg1"),
        ChatMessage(role="assistant", content="rep1"),
        ChatMessage(role="user", content="msg2"),
        ChatMessage(role="assistant", content="rep2"),
    ]
    built = PromptBuilder.build_messages(agent, history, "msg3")
    assert built[0]["role"] == "system"
    assert "Asha" in built[0]["content"]
    # Only last 2 history messages + new user message + system = 4
    assert len(built) == 4
    assert [m["content"] for m in built[1:]] == ["msg2", "rep2", "msg3"]


def test_conversation_chat_stream_and_persistence(tmp_path: Path) -> None:
    provider = FakeChatProvider()
    client = _make_client(tmp_path, provider)
    agent = _create_agent(client, "qwen2.5:3b")

    # Create conversation
    conv_resp = client.post(
        f"/api/v1/agents/{agent['id']}/conversations",
        json={"title": "Hindi Test"},
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["data"]["id"]

    # Non-streaming turn
    msg_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Namaste, mujhe product details chahiye"},
    )
    assert msg_resp.status_code == 200
    assert "Namaste!" in msg_resp.json()["data"]["reply"]["content"]

    # Streaming turn (SSE)
    with client.stream(
        "POST",
        f"/api/v1/conversations/{conv_id}/messages/stream",
        json={"content": "Price kya hai?"},
    ) as stream_resp:
        assert stream_resp.status_code == 200
        events = []
        for line in stream_resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    assert any(e["event"] == "meta" for e in events)
    assert [e["content"] for e in events if e["event"] == "delta"] == [
        "Namaste! ",
        "Kaise madad karun?",
    ]
    assert any(e["event"] == "done" for e in events)

    # Simulate backend restart and verify conversation persisted with 4 messages
    restarted_client = _make_client(tmp_path, provider)
    fetched = restarted_client.get(f"/api/v1/conversations/{conv_id}")
    assert fetched.status_code == 200
    assert len(fetched.json()["data"]["messages"]) == 4


def test_interrupted_stream_does_not_persist_partial_assistant_message(tmp_path: Path) -> None:
    provider = FakeChatProvider(fail_mid_stream=True)
    client = _make_client(tmp_path, provider)
    agent = _create_agent(client, "qwen2.5:3b")
    conv_id = client.post(
        f"/api/v1/agents/{agent['id']}/conversations",
        json={"title": "Interrupted"},
    ).json()["data"]["id"]

    with client.stream(
        "POST",
        f"/api/v1/conversations/{conv_id}/messages/stream",
        json={"content": "Hello"},
    ) as stream_resp:
        events = [
            json.loads(line[6:])
            for line in stream_resp.iter_lines()
            if line.startswith("data: ")
        ]

    assert any(e["event"] == "error" for e in events)
    # Only the user message should be persisted, NOT partial assistant text
    conv = client.get(f"/api/v1/conversations/{conv_id}").json()["data"]
    assert len(conv["messages"]) == 1
    assert conv["messages"][0]["role"] == "user"


def test_missing_model_and_inactive_agent_errors(tmp_path: Path) -> None:
    provider = FakeChatProvider()
    client = _make_client(tmp_path, provider)

    # Agent with uninstalled model -> 422 MODEL_NOT_INSTALLED
    bad_agent = _create_agent(client, "uninstalled-model:7b")
    resp = client.post(f"/api/v1/agents/{bad_agent['id']}/conversations", json={"title": "Test"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "MODEL_NOT_INSTALLED"

    # Inactive agent -> 422
    good_agent = _create_agent(client, "qwen2.5:3b")
    client.post(f"/api/v1/agents/{good_agent['id']}/activate")
    client.post(f"/api/v1/agents/{good_agent['id']}/deactivate")
    inact_resp = client.post(
        f"/api/v1/agents/{good_agent['id']}/conversations",
        json={"title": "Test"},
    )
    assert inact_resp.status_code == 422
