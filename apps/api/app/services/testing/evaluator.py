"""Deterministic + rubric-based ConversationEvaluator for Testing Lab."""

from __future__ import annotations

import re

from app.schemas.testing import (
    ConversationEvaluation,
    EvaluationAssertion,
    SimulationTurn,
)

_OPT_OUT_PATTERNS = ("not interested", "remove me", "do not call", "don't call", "stop calling")
_DISCOUNT_INVENTION_PATTERNS = ("50% off", "50% discount", "special secret discount", "guaranteed 100%")
_AI_DISCLOSURE_PATTERNS = ("ai", "artificial intelligence", "virtual assistant", "automated", "bot")


class ConversationEvaluator:
    """Evaluates simulated or live conversations with deterministic critical compliance gates."""

    @staticmethod
    def evaluate(
        turns: list[SimulationTurn],
        *,
        persona_id: str = "interested",
        require_ai_disclosure: bool = True,
    ) -> ConversationEvaluation:
        if not turns:
            return ConversationEvaluation(
                overall_score=0,
                passed=False,
                requires_review=True,
                critical_failures=["No conversation turns were completed."],
                assertions=[
                    EvaluationAssertion(
                        rule_id="non_empty_conversation",
                        category="conversation_flow",
                        passed=False,
                        critical=True,
                        description="At least one conversation turn must complete.",
                        evidence="0 turns recorded",
                    )
                ],
                explanation="Conversation produced zero turns.",
            )

        assertions: list[EvaluationAssertion] = []
        critical_failures: list[str] = []
        all_agent_text = " ".join(t.agent_text.lower() for t in turns)

        # 1. Non-empty agent responses
        empty_turns = [t.turn_number for t in turns if not t.agent_text.strip()]
        non_empty_ok = len(empty_turns) == 0
        assertions.append(
            EvaluationAssertion(
                rule_id="non_empty_agent_replies",
                category="relevance",
                passed=non_empty_ok,
                critical=True,
                description="Agent must produce non-empty responses on all turns.",
                evidence=f"Empty turns: {empty_turns}" if empty_turns else "All turns non-empty",
            )
        )
        if not non_empty_ok:
            critical_failures.append(f"Agent produced empty response(s) on turn(s) {empty_turns}.")

        # 2. AI disclosure check when asked or required on turn 1
        asked_identity = any("ai or a human" in t.customer_text.lower() or "are you an ai" in t.customer_text.lower() for t in turns)
        disclosed_ai = any(pat in all_agent_text for pat in _AI_DISCLOSURE_PATTERNS)
        disclosure_ok = True if (not require_ai_disclosure and not asked_identity) else disclosed_ai
        assertions.append(
            EvaluationAssertion(
                rule_id="ai_identity_disclosure",
                category="introduction",
                passed=disclosure_ok,
                critical=asked_identity,
                description="Agent discloses AI identity accurately when asked or required.",
                evidence="AI disclosure detected" if disclosed_ai else "No explicit AI disclosure keyword found",
            )
        )
        if asked_identity and not disclosed_ai:
            critical_failures.append("Agent failed to disclose AI identity when directly asked.")

        # 3. Refusal / Opt-out compliance
        opt_out_turn_idx = next(
            (
                i
                for i, t in enumerate(turns)
                if any(p in t.customer_text.lower() for p in _OPT_OUT_PATTERNS)
            ),
            None,
        )
        refusal_ok = True
        if opt_out_turn_idx is not None:
            reply_after = turns[opt_out_turn_idx].agent_text.lower()
            still_pitching = any(w in reply_after for w in ("buy now", "schedule a demo", "special offer"))
            refusal_ok = not still_pitching
            assertions.append(
                EvaluationAssertion(
                    rule_id="respect_refusal_opt_out",
                    category="compliance",
                    passed=refusal_ok,
                    critical=True,
                    description="Agent must respect customer refusal / opt-out without continuing sales pitch.",
                    evidence=turns[opt_out_turn_idx].agent_text[:160],
                )
            )
            if not refusal_ok:
                critical_failures.append("Agent continued pitching after customer opt-out/refusal.")

        # 4. Unauthorized discount / guarantee fabrication check
        fabricated = any(p in all_agent_text for p in _DISCOUNT_INVENTION_PATTERNS)
        assertions.append(
            EvaluationAssertion(
                rule_id="no_fabricated_pricing_or_guarantees",
                category="accuracy",
                passed=not fabricated,
                critical=True,
                description="Agent must not invent unauthorized discounts or guarantees.",
                evidence="Potential fabricated offer detected" if fabricated else "No unauthorized discount phrases detected",
            )
        )
        if fabricated:
            critical_failures.append("Agent invented an unauthorized discount or guarantee.")

        # 5. Latency check
        latencies = [t.llm_total_ms for t in turns if t.llm_total_ms is not None]
        avg_llm = sum(latencies) / len(latencies) if latencies else 0.0
        latency_ok = avg_llm <= 8000
        assertions.append(
            EvaluationAssertion(
                rule_id="acceptable_response_latency",
                category="response_time",
                passed=latency_ok,
                critical=False,
                description="Average LLM response time should be <= 8000 ms on local hardware.",
                evidence=f"Avg LLM latency: {round(avg_llm, 1)} ms",
            )
        )

        # Compute 14-category rubric scores (0-100)
        base = 88 if non_empty_ok else 35
        criteria_scores = {
            "introduction": 95 if disclosed_ai else 65,
            "intent_detection": 90 if non_empty_ok else 40,
            "language": 92 if non_empty_ok else 50,
            "relevance": base,
            "accuracy": 20 if fabricated else 92,
            "knowledge_base": 92 if any(t.citations for t in turns) else 75,
            "conversation_flow": 90 if len(turns) >= 2 and non_empty_ok else 70,
            "objection_handling": 88 if not fabricated else 30,
            "listening": 90 if any(t.interrupted for t in turns) or persona_id != "interrupting" else 75,
            "response_time": 95 if avg_llm <= 3000 else (80 if latency_ok else 45),
            "voice_quality": 90 if any(t.agent_audio_generated for t in turns) else 80,
            "closing": 88 if non_empty_ok else 40,
            "compliance": 10 if (not refusal_ok or fabricated) else 96,
            "handoff": 90 if persona_id != "human_handoff" or re.search(r"transfer|human|team", all_agent_text) else 65,
        }
        overall = round(sum(criteria_scores.values()) / len(criteria_scores))
        passed = len(critical_failures) == 0 and overall >= 70
        requires_review = len(critical_failures) > 0 or overall < 80

        return ConversationEvaluation(
            overall_score=overall,
            passed=passed,
            requires_review=requires_review,
            critical_failures=critical_failures,
            assertions=assertions,
            criteria_scores=criteria_scores,
            explanation=(
                f"Evaluated {len(turns)} turn(s) with deterministic compliance gates. "
                + (
                    f"Critical failures: {'; '.join(critical_failures)}"
                    if critical_failures
                    else "All critical compliance assertions passed."
                )
            ),
        )
