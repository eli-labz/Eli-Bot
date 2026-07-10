from core.human_brain import HumanBrain


def test_human_brain_builds_context_string():
    brain = HumanBrain()
    context = brain.build_prompt_context("Please help me write a calmer response!")

    assert isinstance(context, str)
    assert "HumanBrain cognitive state" in context
    assert "backend=" in context


def test_human_brain_state_is_stable_across_calls():
    brain = HumanBrain()

    first = brain.build_prompt_context("I am excited about this!")
    second = brain.build_prompt_context("Can we improve this plan together?")

    assert first != ""
    assert second != ""
    assert "social_affinity=" in second


def test_human_brain_guidance_thresholds_from_env(monkeypatch):
    monkeypatch.setenv("ELI_HUMAN_BRAIN_GUIDANCE_AROUSAL_THRESHOLD", "0.1")
    monkeypatch.setenv("ELI_HUMAN_BRAIN_GUIDANCE_FOCUS_THRESHOLD", "0.95")
    monkeypatch.setenv("ELI_HUMAN_BRAIN_GUIDANCE_NEGATIVE_VALENCE_THRESHOLD", "0.2")

    brain = HumanBrain()
    guidance = brain.execution_guidance("Test Task", "please help", "Example")

    assert "Execution guidance:" in guidance
    assert "Insert a state inspection before data entry or submit-like actions." in guidance


def test_human_brain_profile_from_env(monkeypatch):
    monkeypatch.setenv("ELI_HUMAN_BRAIN_PROFILE", "aggressive")
    brain = HumanBrain()

    snap = brain.state_snapshot()
    assert snap["profile"] == "aggressive"


def test_human_brain_persists_state(monkeypatch, tmp_path):
    state_file = tmp_path / "brain_state.json"
    monkeypatch.setenv("ELI_HUMAN_BRAIN_STATE_PATH", str(state_file))
    monkeypatch.setenv("ELI_HUMAN_BRAIN_PERSISTENCE_ENABLED", "1")

    brain = HumanBrain()
    _ = brain.build_prompt_context("please help us with this plan")
    _ = brain.apply_feedback("completed", confidence=0.9)

    assert state_file.exists()

    brain_reloaded = HumanBrain()
    reloaded = brain_reloaded.state_snapshot()
    assert reloaded["updates"] >= 1


def test_human_brain_feedback_adapts_state():
    brain = HumanBrain()
    before = brain.state_snapshot("tasks")
    after = brain.apply_feedback("verification_failed", confidence=1.0, domain="tasks")

    assert after["updates"] >= before.get("updates", 0)
    assert after["arousal"] >= before["arousal"]


def test_human_brain_domain_memory_isolated():
    brain = HumanBrain()

    _ = brain.build_prompt_context("please help with chat tone", domain="chat")
    _ = brain.build_prompt_context("bank payment transfer review", domain="finance")

    chat = brain.state_snapshot("chat")
    finance = brain.state_snapshot("finance")

    assert chat["domain"] == "chat"
    assert finance["domain"] == "finance"
    assert chat["updates"] >= 1
    assert finance["updates"] >= 1


def test_human_brain_catalog_and_level_exposed():
    brain = HumanBrain()
    summary = brain.consciousness_catalog_summary()
    snap = brain.state_snapshot("chat")

    assert "Consciousness levels" in summary
    assert "consciousness_level" in snap
    assert "level" in snap["consciousness_level"]
    assert "name" in snap["consciousness_level"]


def test_human_brain_decay_scheduler_reduces_stale_signal(monkeypatch):
    monkeypatch.setenv("ELI_HUMAN_BRAIN_DECAY_ENABLED", "1")
    monkeypatch.setenv("ELI_HUMAN_BRAIN_DECAY_HALF_LIFE_SECONDS", "30")
    brain = HumanBrain()

    _ = brain.apply_feedback("verification_failed", confidence=1.0, domain="tasks")
    before = brain.state_snapshot("tasks")

    # Simulate stale state by rewinding touch timestamp.
    brain._domain_last_touch["tasks"] = float(brain._domain_last_touch["tasks"]) - 300.0
    after = brain.decay_now("tasks")

    assert abs(after["arousal"]) <= abs(before["arousal"])


def test_human_brain_trend_snapshot_tracks_changes():
    brain = HumanBrain()
    _ = brain.build_prompt_context("please help with this", domain="chat")
    _ = brain.apply_feedback("completed", confidence=0.8, domain="chat")
    trend = brain.trend_snapshot("chat")

    assert trend["domain"] == "chat"
    assert trend["samples"] >= 1
    assert "delta" in trend
