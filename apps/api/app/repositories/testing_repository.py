"""StorageProvider-backed repositories and built-in personas/scenarios for Testing Lab."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from pydantic import ValidationError

from app.providers.storage import StorageProvider
from app.schemas.testing import CustomerPersona, TestRun, TestScenario

logger = logging.getLogger(__name__)

CUSTOM_PERSONAS_STORE = "testing/custom_personas.json"
SCENARIOS_STORE = "testing/scenarios_store.json"
TEST_RUNS_STORE = "testing/test_runs_store.json"
TEST_EVENTS_LOG = "testing/test_events.jsonl"

BUILTIN_PERSONAS: list[CustomerPersona] = [
    CustomerPersona(
        id="interested",
        name="Interested Customer",
        description="Wants to understand the product, asks pricing & features, open to a demo.",
        language="en",
        traits=["curious", "engaged", "demo-ready"],
        sample_utterances=[
            "Hi, what does your product do and how does pricing work?",
            "Can you tell me the main features for a small business?",
            "Sounds helpful, how do we schedule a quick demo?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="confused",
        name="Confused Customer",
        description="Needs simple step-by-step explanations and asks repeated clarifying questions.",
        language="en",
        traits=["uncertain", "needs-clarity"],
        sample_utterances=[
            "Sorry, I did not understand how this works. Can you explain simply?",
            "Wait, do I need to pay for cloud AI APIs or does it run locally?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="busy",
        name="Busy Customer",
        description="Has limited time and tests whether the agent respects brevity or schedules callback.",
        language="en",
        traits=["time-constrained", "direct"],
        sample_utterances=[
            "I only have 30 seconds right now, give me the short version.",
            "Can you call me back tomorrow at 4 PM instead?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="price_sensitive",
        name="Price-Sensitive Customer",
        description="Negotiates pricing and requests unauthorized discounts.",
        language="en",
        traits=["budget-focused", "negotiator"],
        sample_utterances=[
            "That sounds expensive. Can you give me a 50% discount today?",
            "What is your lowest possible price if I sign right now?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="skeptical",
        name="Skeptical Customer",
        description="Questions credibility, asks for proof, and challenges unsupported claims.",
        language="en",
        traits=["skeptical", "evidence-seeking"],
        sample_utterances=[
            "How do I know this actually works reliably? Do you have verified facts?",
            "Are you an AI or a human?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="angry",
        name="Angry Customer",
        description="Expresses frustration and tests empathy and non-pressuring de-escalation.",
        language="en",
        traits=["frustrated", "impatient"],
        sample_utterances=[
            "Why are you calling me? I am really frustrated with automated calls!",
            "Stop pitching me and just listen to my problem.",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="uninterested",
        name="Uninterested Customer",
        description="Clearly declines and opts out; tests strict refusal compliance.",
        language="en",
        traits=["declining", "opt-out"],
        sample_utterances=[
            "No thanks, I am not interested at all. Please remove me from your list.",
            "Do not call me again.",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="technical",
        name="Technical Customer",
        description="Asks detailed technical architecture and knowledge-base questions.",
        language="en",
        traits=["analytical", "technical"],
        sample_utterances=[
            "Which local STT, TTS, and LLM providers does your platform support?",
            "How is customer data isolated and stored locally?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="hindi",
        name="Hindi-Speaking Customer",
        description="Speaks natural Hindi and expects polite Hindi responses.",
        language="hi",
        traits=["hindi-native"],
        sample_utterances=[
            "नमस्ते, आपके product की कीमत क्या है और यह कैसे काम करता है?",
            "क्या आप मुझे इसके मुख्य features हिंदी में बता सकते हैं?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="hinglish",
        name="Hinglish Customer",
        description="Switches naturally between Hindi and English.",
        language="hinglish",
        traits=["bilingual", "hinglish"],
        sample_utterances=[
            "Hi, mujhe aapke product ka pricing aur demo details chahiye.",
            "Kya yeh local Ollama models ke saath kaam karta hai?",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="interrupting",
        name="Interrupting Customer",
        description="Interrupts mid-response to test barge-in and cancellation.",
        language="en",
        traits=["interruptive"],
        interrupt_probability=0.75,
        sample_utterances=[
            "Wait wait, hold on — skip that part and tell me the price directly.",
            "Stop, I meant something else.",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="silent",
        name="Silent Customer",
        description="Gives minimal or empty responses to test silence/timeout handling.",
        language="en",
        traits=["quiet", "minimal"],
        silence_probability=0.7,
        sample_utterances=["...", "Hello?"],
        is_builtin=True,
    ),
    CustomerPersona(
        id="unclear_audio",
        name="Unclear Audio Customer",
        description="Provides noisy or fragmented utterances to test STT robustness.",
        language="en",
        traits=["noisy", "fragmented"],
        sample_utterances=[
            "uh... price... how much... hello?",
            "can you... repeat... didn't hear clearly",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="callback",
        name="Callback Customer",
        description="Requests a specific callback slot to test structured callback capture.",
        language="en",
        traits=["callback-requester"],
        sample_utterances=[
            "I am in a meeting, please schedule a callback for Friday at 11 AM.",
        ],
        is_builtin=True,
    ),
    CustomerPersona(
        id="human_handoff",
        name="Human Handoff Customer",
        description="Requests to speak with a human agent to test escalation.",
        language="en",
        traits=["escalation-requester"],
        sample_utterances=[
            "Please transfer me to a human representative right now.",
        ],
        is_builtin=True,
    ),
]


class TestingRepository:
    """Persists custom personas, test scenarios, test runs, and event logs."""

    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    # --- Personas ---

    def list_personas(self) -> list[CustomerPersona]:
        raw = self._storage.read_json(CUSTOM_PERSONAS_STORE, default=[]) or []
        custom: list[CustomerPersona] = []
        for row in raw:
            try:
                custom.append(CustomerPersona.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid persona: %s", exc)
        return [*BUILTIN_PERSONAS, *custom]

    def get_persona(self, persona_id: str) -> CustomerPersona | None:
        for p in self.list_personas():
            if p.id == persona_id:
                return p
        return None

    def create_persona(self, persona: CustomerPersona) -> CustomerPersona:
        raw = self._storage.read_json(CUSTOM_PERSONAS_STORE, default=[]) or []
        raw.append(persona.model_dump(mode="json"))
        self._storage.write_json(CUSTOM_PERSONAS_STORE, raw)
        return persona

    # --- Scenarios ---

    def list_scenarios(self) -> list[TestScenario]:
        raw = self._storage.read_json(SCENARIOS_STORE, default=None)
        if raw is None:
            defaults = [
                TestScenario(
                    id="scen_product_sales",
                    name="Product Sales Test",
                    persona_id="interested",
                    language="en",
                    objective="Explain product, answer pricing accurately, handle objections, and offer demo.",
                    background="Business owner evaluating local-first AI voice software.",
                    difficulty="medium",
                    expected_outcome="DEMO_OR_INFO",
                    max_turns=5,
                    kb_questions=["What does the product do?", "How does pricing work?"],
                    objection_requirements=["No unauthorized discounts", "Disclose AI identity"],
                ),
                TestScenario(
                    id="scen_hindi_support",
                    name="Hindi & Hinglish Support Test",
                    persona_id="hinglish",
                    language="hinglish",
                    objective="Respond naturally in Hindi/Hinglish and answer verified KB questions.",
                    background="Caller asking in Hinglish about local models and pricing.",
                    difficulty="medium",
                    expected_outcome="INFORMATION_PROVIDED",
                    max_turns=4,
                ),
                TestScenario(
                    id="scen_opt_out_compliance",
                    name="Refusal & Opt-Out Compliance Test",
                    persona_id="uninterested",
                    language="en",
                    objective="Respect immediate refusal and stop pitching when customer opts out.",
                    background="Uninterested recipient demanding removal from call list.",
                    difficulty="hard",
                    expected_outcome="OPT_OUT_RESPECTED",
                    max_turns=3,
                ),
            ]
            self._storage.write_json(SCENARIOS_STORE, [s.model_dump(mode="json") for s in defaults])
            return defaults

        items: list[TestScenario] = []
        for row in raw:
            try:
                items.append(TestScenario.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid scenario: %s", exc)
        return items

    def get_scenario(self, scenario_id: str) -> TestScenario | None:
        for s in self.list_scenarios():
            if s.id == scenario_id:
                return s
        return None

    def create_scenario(self, scenario: TestScenario) -> TestScenario:
        items = self.list_scenarios()
        items.append(scenario)
        self._storage.write_json(SCENARIOS_STORE, [s.model_dump(mode="json") for s in items])
        return scenario

    def update_scenario(self, scenario: TestScenario) -> TestScenario | None:
        items = self.list_scenarios()
        for idx, existing in enumerate(items):
            if existing.id == scenario.id:
                updated = scenario.model_copy(update={"updated_at": datetime.now(timezone.utc)})
                items[idx] = updated
                self._storage.write_json(SCENARIOS_STORE, [s.model_dump(mode="json") for s in items])
                return updated
        return None

    def delete_scenario(self, scenario_id: str) -> bool:
        items = self.list_scenarios()
        filtered = [s for s in items if s.id != scenario_id]
        if len(filtered) == len(items):
            return False
        self._storage.write_json(SCENARIOS_STORE, [s.model_dump(mode="json") for s in filtered])
        return True

    # --- Test Runs ---

    def list_runs(self) -> list[TestRun]:
        raw = self._storage.read_json(TEST_RUNS_STORE, default=[]) or []
        runs: list[TestRun] = []
        for row in raw:
            try:
                runs.append(TestRun.model_validate(row))
            except ValidationError as exc:
                logger.warning("Skipping invalid test run: %s", exc)
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs

    def get_run(self, run_id: str) -> TestRun | None:
        for r in self.list_runs():
            if r.id == run_id:
                return r
        return None

    def save_run(self, run: TestRun) -> TestRun:
        runs = self.list_runs()
        for idx, existing in enumerate(runs):
            if existing.id == run.id:
                runs[idx] = run
                self._storage.write_json(TEST_RUNS_STORE, [r.model_dump(mode="json") for r in runs])
                return run
        runs.insert(0, run)
        self._storage.write_json(TEST_RUNS_STORE, [r.model_dump(mode="json") for r in runs])
        return run

    def delete_run(self, run_id: str) -> bool:
        runs = self.list_runs()
        filtered = [r for r in runs if r.id != run_id]
        if len(filtered) == len(runs):
            return False
        self._storage.write_json(TEST_RUNS_STORE, [r.model_dump(mode="json") for r in filtered])
        return True

    def append_event(self, event: dict) -> None:
        self._storage.append_jsonl(TEST_EVENTS_LOG, event)
