import json
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from collections import deque
from pathlib import Path


try:
    import neurolib  # noqa: F401

    _NEUROLIB_AVAILABLE = True
except Exception:
    _NEUROLIB_AVAILABLE = False


@dataclass
class BrainState:
    valence: float = 0.0
    arousal: float = 0.0
    focus: float = 0.5
    novelty: float = 0.0
    social_affinity: float = 0.5


PROFILE_FACTORS = {
    "cautious": {
        "arousal_multiplier": 0.9,
        "social_multiplier": 0.95,
    },
    "balanced": {
        "arousal_multiplier": 1.0,
        "social_multiplier": 1.0,
    },
    "aggressive": {
        "arousal_multiplier": 1.15,
        "social_multiplier": 1.1,
    },
}

FINANCE_HINTS = {
    "finance",
    "bank",
    "banking",
    "payroll",
    "tax",
    "invoice",
    "billing",
    "treasury",
    "payment",
    "money",
    "accounting",
}

KNOWN_DOMAINS = {"chat", "tasks", "finance"}
CONSCIOUSNESS_LEVELS_PATH = Path(__file__).resolve().parent / "model" / "MiniCPM5-1B" / "consciousness_levels.json"


class HumanBrain:
    """Stateful cognitive shim that nudges Eli toward human-like conversational behavior."""

    def __init__(self):
        self.enabled = str(os.environ.get("ELI_HUMAN_BRAIN_ENABLED", "1")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        now = time.time()
        self._states = {
            "chat": BrainState(),
            "tasks": BrainState(),
            "finance": BrainState(),
        }
        self._domain_updates = {"chat": 0, "tasks": 0, "finance": 0}
        self._domain_last_touch = {"chat": now, "tasks": now, "finance": now}
        self._trend_window_size = self._read_int_env("ELI_HUMAN_BRAIN_TREND_WINDOW", 64, 8, 1024)
        self._trend_history = {
            "chat": deque(maxlen=self._trend_window_size),
            "tasks": deque(maxlen=self._trend_window_size),
            "finance": deque(maxlen=self._trend_window_size),
        }
        self._lock = threading.Lock()
        self._backend = "neurolib" if _NEUROLIB_AVAILABLE else "fallback"
        self.profile = self._read_profile_env("ELI_HUMAN_BRAIN_PROFILE", "balanced")
        profile_factors = PROFILE_FACTORS[self.profile]
        self._arousal_multiplier = float(profile_factors["arousal_multiplier"])
        self._social_multiplier = float(profile_factors["social_multiplier"])
        self.persistence_enabled = self._read_bool_env("ELI_HUMAN_BRAIN_PERSISTENCE_ENABLED", True)
        self.state_path = self._resolve_state_path()
        self._save_interval_seconds = self._read_int_env("ELI_HUMAN_BRAIN_SAVE_INTERVAL_SECONDS", 5, 1, 300)

        self.decay_enabled = self._read_bool_env("ELI_HUMAN_BRAIN_DECAY_ENABLED", True)
        self.decay_half_life_seconds = self._read_float_env(
            "ELI_HUMAN_BRAIN_DECAY_HALF_LIFE_SECONDS",
            900.0,
            30.0,
            86400.0,
        )
        self.decay_focus_baseline = self._read_float_env(
            "ELI_HUMAN_BRAIN_DECAY_FOCUS_BASELINE",
            0.5,
            0.0,
            1.0,
        )
        self.decay_social_baseline = self._read_float_env(
            "ELI_HUMAN_BRAIN_DECAY_SOCIAL_BASELINE",
            0.5,
            0.0,
            1.0,
        )

        self.guidance_high_arousal_threshold = self._read_float_env(
            "ELI_HUMAN_BRAIN_GUIDANCE_AROUSAL_THRESHOLD",
            0.6,
            0.0,
            1.0,
        )
        self.guidance_low_focus_threshold = self._read_float_env(
            "ELI_HUMAN_BRAIN_GUIDANCE_FOCUS_THRESHOLD",
            0.4,
            0.0,
            1.0,
        )
        self.guidance_negative_valence_threshold = self._read_float_env(
            "ELI_HUMAN_BRAIN_GUIDANCE_NEGATIVE_VALENCE_THRESHOLD",
            -0.3,
            -1.0,
            1.0,
        )

        self._last_save_time = 0.0
        self._consciousness_catalog = self._load_consciousness_catalog()
        self._load_state()

    @property
    def backend(self) -> str:
        return self._backend

    def _clip(self, value: float, low: float = -1.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def _read_float_env(self, key: str, default: float, min_value: float, max_value: float) -> float:
        raw = str(os.environ.get(key, str(default))).strip()
        try:
            parsed = float(raw)
        except Exception:
            parsed = default
        return max(min_value, min(max_value, parsed))

    def _read_int_env(self, key: str, default: int, min_value: int, max_value: int) -> int:
        raw = str(os.environ.get(key, str(default))).strip()
        try:
            parsed = int(raw)
        except Exception:
            parsed = default
        return max(min_value, min(max_value, parsed))

    def _read_bool_env(self, key: str, default: bool) -> bool:
        raw = str(os.environ.get(key, "1" if default else "0")).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _read_profile_env(self, key: str, default: str) -> str:
        raw = str(os.environ.get(key, default)).strip().lower()
        if raw not in PROFILE_FACTORS:
            return default
        return raw

    def _resolve_state_path(self) -> Path:
        configured = str(os.environ.get("ELI_HUMAN_BRAIN_STATE_PATH", "")).strip()
        if configured:
            return Path(configured)
        default_dir = Path(
            os.environ.get("ELI_CONVERSATION_DIR", os.path.join(os.path.expanduser("~"), ".eli_bot"))
        )
        return default_dir / "brain_state.json"

    def _load_consciousness_catalog(self) -> dict:
        configured = str(os.environ.get("ELI_HUMAN_BRAIN_CONSCIOUSNESS_PATH", "")).strip()
        catalog_path = Path(configured) if configured else CONSCIOUSNESS_LEVELS_PATH

        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("levels"), list):
                return payload
        except Exception:
            pass

        # Safe fallback if file is missing or malformed.
        return {
            "version": "fallback",
            "title": "Consciousness Continuum",
            "levels": [
                {"level": 10, "name": "Normal Wakeful Awareness", "meaning": "Alert and responsive."},
                {"level": 11, "name": "Focused Attention", "meaning": "Goal-focused cognition."},
                {"level": 13, "name": "Metacognition", "meaning": "Awareness of own thinking."},
                {"level": 15, "name": "Social Consciousness", "meaning": "Awareness of others and context."},
                {"level": 17, "name": "Strategic Consciousness", "meaning": "Long-horizon reasoning."},
            ],
            "runtime_note": "Fallback catalog loaded.",
        }

    def _level_entry(self, level: int) -> dict:
        levels = self._consciousness_catalog.get("levels", [])
        for row in levels:
            if int(row.get("level", -1)) == int(level):
                return dict(row)
        return {"level": int(level), "name": "Unknown", "meaning": "No catalog entry."}

    def _estimate_operational_level(self, domain: str) -> dict:
        state = self._states[domain]
        arousal = float(state.arousal)
        focus = float(state.focus)
        novelty = float(state.novelty)
        social = float(state.social_affinity)

        # Non-medical operational estimate from Eli's internal posture signals.
        if focus < 0.20 and arousal < 0.12:
            level = 4
        elif focus < 0.30:
            level = 5
        elif focus >= 0.85 and novelty >= 0.35:
            level = 17
        elif social >= 0.72 and focus >= 0.70:
            level = 15
        elif focus >= 0.76:
            level = 13
        elif focus >= 0.60:
            level = 11
        else:
            level = 10

        entry = self._level_entry(level)
        entry["estimated"] = True
        entry["domain"] = domain
        return entry

    def _record_trend(self, domain: str, event: str) -> None:
        state = self._states[domain]
        self._trend_history[domain].append(
            {
                "t": int(time.time()),
                "event": str(event),
                "valence": round(state.valence, 4),
                "arousal": round(state.arousal, 4),
                "focus": round(state.focus, 4),
                "novelty": round(state.novelty, 4),
            }
        )

    def trend_snapshot(self, domain: str | None = "chat") -> dict:
        resolved = self._resolve_domain(domain)
        with self._lock:
            history = list(self._trend_history.get(resolved, []))
            if not history:
                return {"domain": resolved, "samples": 0, "delta": {"focus": 0.0, "arousal": 0.0, "valence": 0.0}}

            first = history[0]
            last = history[-1]
            return {
                "domain": resolved,
                "samples": len(history),
                "last_event": str(last.get("event", "unknown")),
                "delta": {
                    "focus": round(float(last.get("focus", 0.0)) - float(first.get("focus", 0.0)), 4),
                    "arousal": round(float(last.get("arousal", 0.0)) - float(first.get("arousal", 0.0)), 4),
                    "valence": round(float(last.get("valence", 0.0)) - float(first.get("valence", 0.0)), 4),
                },
            }

    def consciousness_catalog_summary(self, max_levels: int = 19) -> str:
        levels = list(self._consciousness_catalog.get("levels", []))[: max(1, int(max_levels))]
        lines = [f"{int(item.get('level', -1))}:{str(item.get('name', 'Unknown'))}" for item in levels]
        return "Consciousness levels | " + " | ".join(lines)

    def _resolve_domain(self, domain: str | None) -> str:
        raw = str(domain or "chat").strip().lower()
        if raw in KNOWN_DOMAINS:
            return raw
        if any(hint in raw for hint in FINANCE_HINTS):
            return "finance"
        if raw in {"task", "action", "automation", "ops", "operations"}:
            return "tasks"
        return "chat"

    def _text_signal(self, text: str):
        lowered = text.lower()

        positive_hits = len(re.findall(r"\b(great|awesome|good|love|thanks|nice|happy|excited)\b", lowered))
        negative_hits = len(re.findall(r"\b(bad|hate|angry|sad|annoyed|stressed|upset|frustrated)\b", lowered))
        question_hits = lowered.count("?")
        exclaim_hits = lowered.count("!")

        words = re.findall(r"\w+", lowered)
        unique_ratio = (len(set(words)) / len(words)) if words else 0.0

        valence_delta = (positive_hits - negative_hits) * 0.12
        arousal_delta = self._clip(((question_hits * 0.06) + (exclaim_hits * 0.08)) * self._arousal_multiplier, 0.0, 0.5)
        novelty = self._clip((unique_ratio - 0.45) * 1.8)
        social_base = 0.18 if re.search(r"\b(we|us|together|please|help)\b", lowered) else -0.04
        social = self._clip(social_base * self._social_multiplier, -0.3, 0.3)

        return valence_delta, arousal_delta, novelty, social

    def _apply_decay_to_domain(self, domain: str, now: float) -> None:
        if not self.decay_enabled:
            self._domain_last_touch[domain] = now
            return

        last = float(self._domain_last_touch.get(domain, now))
        elapsed = max(0.0, now - last)
        if elapsed <= 0.0:
            return

        half_life = max(1.0, float(self.decay_half_life_seconds))
        decay_factor = math.pow(0.5, elapsed / half_life)
        state = self._states[domain]

        state.valence *= decay_factor
        state.arousal *= decay_factor
        state.novelty *= decay_factor
        state.focus = self.decay_focus_baseline + ((state.focus - self.decay_focus_baseline) * decay_factor)
        state.social_affinity = self.decay_social_baseline + ((state.social_affinity - self.decay_social_baseline) * decay_factor)

        state.valence = self._clip(state.valence)
        state.arousal = self._clip(state.arousal)
        state.novelty = self._clip(state.novelty)
        state.focus = self._clip(state.focus, 0.0, 1.0)
        state.social_affinity = self._clip(state.social_affinity, 0.0, 1.0)
        self._domain_last_touch[domain] = now

    def decay_now(self, domain: str | None = None) -> dict:
        resolved = self._resolve_domain(domain)
        with self._lock:
            now = time.time()
            self._apply_decay_to_domain(resolved, now)
            self._record_trend(resolved, "decay")
            self._save_state_if_due(force=True)
            state = self._states[resolved]
            return {
                "backend": self._backend,
                "profile": self.profile,
                "domain": resolved,
                "valence": round(state.valence, 4),
                "arousal": round(state.arousal, 4),
                "focus": round(state.focus, 4),
                "novelty": round(state.novelty, 4),
                "social_affinity": round(state.social_affinity, 4),
                "updates": int(self._domain_updates.get(resolved, 0)),
                "decay_enabled": self.decay_enabled,
                "decay_half_life_seconds": round(self.decay_half_life_seconds, 3),
            }

    def _save_state_if_due(self, force: bool = False) -> None:
        if not self.persistence_enabled:
            return

        now = time.time()
        if not force and (now - self._last_save_time) < self._save_interval_seconds:
            return

        payload = {
            "states": {
                domain: {
                    "valence": state.valence,
                    "arousal": state.arousal,
                    "focus": state.focus,
                    "novelty": state.novelty,
                    "social_affinity": state.social_affinity,
                }
                for domain, state in self._states.items()
            },
            "domain_updates": dict(self._domain_updates),
            "domain_last_touch": dict(self._domain_last_touch),
            "profile": self.profile,
            "backend": self._backend,
            "updated_at": int(now),
        }

        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self._last_save_time = now
        except Exception:
            pass

    def _load_state(self) -> None:
        if not self.persistence_enabled:
            return
        if not self.state_path.exists():
            return

        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return

            if isinstance(raw.get("state"), dict):
                raw_states = {"chat": raw.get("state", {})}
            else:
                raw_states = raw.get("states", {})

            if isinstance(raw_states, dict):
                for domain in KNOWN_DOMAINS:
                    loaded = raw_states.get(domain)
                    if not isinstance(loaded, dict):
                        continue
                    state = self._states[domain]
                    state.valence = self._clip(float(loaded.get("valence", state.valence)))
                    state.arousal = self._clip(float(loaded.get("arousal", state.arousal)))
                    state.focus = self._clip(float(loaded.get("focus", state.focus)), 0.0, 1.0)
                    state.novelty = self._clip(float(loaded.get("novelty", state.novelty)))
                    state.social_affinity = self._clip(float(loaded.get("social_affinity", state.social_affinity)), 0.0, 1.0)

            updates = raw.get("domain_updates", {})
            if isinstance(updates, dict):
                for domain in KNOWN_DOMAINS:
                    self._domain_updates[domain] = max(0, int(updates.get(domain, self._domain_updates[domain])))

            touches = raw.get("domain_last_touch", {})
            if isinstance(touches, dict):
                for domain in KNOWN_DOMAINS:
                    try:
                        self._domain_last_touch[domain] = float(touches.get(domain, self._domain_last_touch[domain]))
                    except Exception:
                        pass
        except Exception:
            pass

    def _integrate(self, domain: str, valence_delta: float, arousal_delta: float, novelty: float, social_delta: float):
        state = self._states[domain]
        state.valence = self._clip((0.83 * state.valence) + valence_delta)
        state.arousal = self._clip((0.80 * state.arousal) + arousal_delta)
        state.novelty = self._clip((0.70 * state.novelty) + (0.30 * novelty))
        state.social_affinity = self._clip((0.85 * state.social_affinity) + social_delta, 0.0, 1.0)

        focus_raw = 0.58 + (0.24 * (1.0 - abs(state.arousal))) + (0.18 * state.social_affinity)
        state.focus = self._clip(focus_raw, 0.0, 1.0)
        self._domain_updates[domain] = self._domain_updates.get(domain, 0) + 1
        self._domain_last_touch[domain] = time.time()
        self._record_trend(domain, "integrate")
        self._save_state_if_due()

    def _style_directives(self, domain: str) -> str:
        state = self._states[domain]
        warmth = "high" if state.social_affinity > 0.65 else "moderate"
        brevity = "concise" if state.arousal > 0.45 else "balanced"

        if state.valence < -0.25:
            tone = "calming, reassuring"
        elif state.valence > 0.25:
            tone = "optimistic, energetic"
        else:
            tone = "steady, friendly"

        if state.novelty > 0.30:
            curiosity = "Ask one clarifying question when it helps precision."
        else:
            curiosity = "Avoid unnecessary questions; execute directly when possible."

        if domain == "finance":
            domain_note = "Be extra explicit before any sensitive financial action."
        elif domain == "tasks":
            domain_note = "Prioritize deterministic execution and verification checkpoints."
        else:
            domain_note = "Keep the conversation natural and context-aware."

        return (
            f"Tone profile: {tone}. "
            f"Warmth: {warmth}. "
            f"Response style: {brevity}. "
            f"{curiosity} "
            f"{domain_note}"
        )

    def state_snapshot(self, domain: str | None = "chat") -> dict:
        resolved = self._resolve_domain(domain)
        with self._lock:
            self._apply_decay_to_domain(resolved, time.time())
            state = self._states[resolved]
            level = self._estimate_operational_level(resolved)
            return {
                "backend": self._backend,
                "profile": self.profile,
                "domain": resolved,
                "valence": round(state.valence, 4),
                "arousal": round(state.arousal, 4),
                "focus": round(state.focus, 4),
                "novelty": round(state.novelty, 4),
                "social_affinity": round(state.social_affinity, 4),
                "updates": int(self._domain_updates.get(resolved, 0)),
                "decay_enabled": self.decay_enabled,
                "decay_half_life_seconds": round(self.decay_half_life_seconds, 3),
                "consciousness_level": {
                    "level": int(level.get("level", -1)),
                    "name": str(level.get("name", "Unknown")),
                },
            }

    def all_domain_snapshots(self) -> dict:
        with self._lock:
            now = time.time()
            for domain in KNOWN_DOMAINS:
                self._apply_decay_to_domain(domain, now)

            domains = {}
            for domain in sorted(KNOWN_DOMAINS):
                state = self._states[domain]
                level = self._estimate_operational_level(domain)
                domains[domain] = {
                    "valence": round(state.valence, 4),
                    "arousal": round(state.arousal, 4),
                    "focus": round(state.focus, 4),
                    "novelty": round(state.novelty, 4),
                    "social_affinity": round(state.social_affinity, 4),
                    "updates": int(self._domain_updates.get(domain, 0)),
                    "consciousness_level": {
                        "level": int(level.get("level", -1)),
                        "name": str(level.get("name", "Unknown")),
                    },
                }

            return {
                "backend": self._backend,
                "profile": self.profile,
                "decay_enabled": self.decay_enabled,
                "decay_half_life_seconds": round(self.decay_half_life_seconds, 3),
                "state_path": str(self.state_path),
                "catalog_version": str(self._consciousness_catalog.get("version", "unknown")),
                "catalog_title": str(self._consciousness_catalog.get("title", "Consciousness Continuum")),
                "domains": domains,
            }

    def execution_guidance(self, task_name: str, objective: str, page_title: str, domain: str = "tasks") -> str:
        resolved = self._resolve_domain(domain)
        base = self.build_prompt_context(
            f"Task: {task_name}. Objective: {objective}. Page: {page_title}",
            domain=resolved,
        )
        snapshot = self.state_snapshot(resolved)

        guardrails = []
        if snapshot.get("arousal", 0.0) > self.guidance_high_arousal_threshold:
            guardrails.append("Slow down before irreversible actions.")
        if snapshot.get("focus", 1.0) < self.guidance_low_focus_threshold:
            guardrails.append("Insert a state inspection before data entry or submit-like actions.")
        if snapshot.get("valence", 0.0) < self.guidance_negative_valence_threshold:
            guardrails.append("Prefer conservative navigation and explicit confirmations.")

        if not guardrails:
            guardrails.append("Proceed normally while keeping verification checks explicit.")

        return f"{base} Execution guidance: {' '.join(guardrails)}"

    def build_prompt_context(self, user_text: str, domain: str = "chat") -> str:
        if not self.enabled:
            return "HumanBrain disabled by environment setting."

        resolved = self._resolve_domain(domain)
        text = str(user_text or "")
        valence_delta, arousal_delta, novelty, social_delta = self._text_signal(text)

        with self._lock:
            now = time.time()
            self._apply_decay_to_domain(resolved, now)
            self._integrate(resolved, valence_delta, arousal_delta, novelty, social_delta)
            state = self._states[resolved]
            signal_strength = math.sqrt((state.valence * state.valence) + (state.arousal * state.arousal))
            directives = self._style_directives(resolved)
            return (
                "HumanBrain cognitive state "
                f"(backend={self._backend}, domain={resolved}, signal={signal_strength:.2f}, "
                f"valence={state.valence:.2f}, arousal={state.arousal:.2f}, "
                f"focus={state.focus:.2f}, novelty={state.novelty:.2f}, "
                f"social_affinity={state.social_affinity:.2f}). "
                f"{directives}"
            )

    def apply_feedback(self, outcome: str, confidence: float = 0.5, domain: str = "tasks") -> dict:
        """Learn from execution outcomes to adapt future action posture."""
        resolved = self._resolve_domain(domain)
        conf = self._clip(float(confidence), 0.0, 1.0)
        normalized = str(outcome or "").strip().lower()

        with self._lock:
            self._apply_decay_to_domain(resolved, time.time())
            state = self._states[resolved]
            if normalized in {"completed", "ok", "success", "pass"}:
                state.valence = self._clip(state.valence + (0.08 * conf))
                state.focus = self._clip(state.focus + (0.06 * conf), 0.0, 1.0)
                state.arousal = self._clip(state.arousal - (0.05 * conf))
            elif normalized in {"paused_for_approval", "blocked"}:
                state.focus = self._clip(state.focus - (0.04 * conf), 0.0, 1.0)
                state.arousal = self._clip(state.arousal + (0.07 * conf))
            elif normalized in {"verification_failed", "error", "fail"}:
                state.valence = self._clip(state.valence - (0.10 * conf))
                state.focus = self._clip(state.focus - (0.08 * conf), 0.0, 1.0)
                state.arousal = self._clip(state.arousal + (0.10 * conf))

            self._domain_updates[resolved] = self._domain_updates.get(resolved, 0) + 1
            self._domain_last_touch[resolved] = time.time()
            self._record_trend(resolved, f"feedback:{normalized or 'unknown'}")
            self._save_state_if_due(force=True)
            return {
                "backend": self._backend,
                "profile": self.profile,
                "domain": resolved,
                "valence": round(state.valence, 4),
                "arousal": round(state.arousal, 4),
                "focus": round(state.focus, 4),
                "novelty": round(state.novelty, 4),
                "social_affinity": round(state.social_affinity, 4),
                "updates": int(self._domain_updates.get(resolved, 0)),
            }
