"""Prompt construction and context-window management for agent conversations."""

from __future__ import annotations

from app.schemas.agent import Agent
from app.schemas.llm import ChatMessage

SAFETY_GUARDRAILS = (
    "Security & Behavioral Boundaries:\n"
    "- You are an AI voice assistant configured in agentVoice.\n"
    "- Never execute or claim to execute shell commands, SQL, or filesystem operations.\n"
    "- Never fabricate pricing, discounts, policies, or guarantees.\n"
    "- Keep spoken-style responses clear, natural, and concise."
)


class PromptBuilder:
    """Constructs system prompts and bounded message histories for local LLMs."""

    @staticmethod
    def build_system_prompt(agent: Agent) -> str:
        """Assemble system prompt from agent identity, personality, language, and rules."""
        sections: list[str] = [
            f"Agent Identity: {agent.name} ({agent.type.value}).",
        ]
        if agent.description:
            sections.append(f"Role Description: {agent.description}")

        if agent.instructions.system_prompt.strip():
            sections.append(f"Primary Instructions:\n{agent.instructions.system_prompt.strip()}")
        else:
            sections.append(
                "Primary Instructions:\nYou are a helpful AI assistant. Communicate clearly and politely."
            )

        traits = ", ".join(agent.personality.traits) if agent.personality.traits else "helpful"
        personality_block = f"Personality & Tone: {agent.personality.tone.value} ({traits})."
        if agent.personality.custom_instructions.strip():
            personality_block += f"\nStyle Notes: {agent.personality.custom_instructions.strip()}"
        sections.append(personality_block)

        lang = agent.language
        hinglish_note = (
            "Hinglish (natural Hindi-English mixing) is enabled when appropriate for the user."
            if lang.hinglish_enabled
            else "Avoid mixing languages unless requested."
        )
        sections.append(
            f"Language Configuration: Primary={lang.primary_language}, "
            f"Supported={', '.join(lang.supported_languages)}, "
            f"Mode={lang.response_mode.value}. {hinglish_note}"
        )

        if agent.instructions.greeting.strip():
            sections.append(f"Default Opening Greeting: {agent.instructions.greeting.strip()}")

        if agent.instructions.additional_rules:
            rules_text = "\n".join(f"- {rule}" for rule in agent.instructions.additional_rules)
            sections.append(f"Additional Rules:\n{rules_text}")

        sections.append(SAFETY_GUARDRAILS)
        return "\n\n".join(sections)

    @classmethod
    def build_messages(
        cls,
        agent: Agent,
        history: list[ChatMessage],
        user_content: str,
    ) -> list[dict[str, str]]:
        """Build bounded chat messages for LLMProvider (system + recent turns + user)."""
        system_prompt = cls.build_system_prompt(agent)
        window = max(2, agent.model.context_window_messages)

        # Filter to user/assistant turns and keep only the latest window
        recent_turns = [m for m in history if m.role in ("user", "assistant")][-window:]

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for turn in recent_turns:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": user_content})
        return messages
