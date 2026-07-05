from pathlib import Path

AUTORESEARCH_PROGRAM = (
    Path(__file__).resolve().parent / "third_party" / "autoresearch-master" / "program.md"
)


def get_autoresearch_policy_context(max_chars=800):
    if not AUTORESEARCH_PROGRAM.exists():
        return ""

    try:
        content = AUTORESEARCH_PROGRAM.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

    policy = (
        "Autonomous policy: prefer OS-native/UIA semantic interaction over OCR or imaging, "
        "iterate and self-correct actions by observed system state, and preserve deterministic, "
        "stepwise planning for reliable GUI execution."
    )

    source_excerpt = " ".join(content.splitlines()[:18]).strip()
    source_excerpt = " ".join(source_excerpt.split())
    source_excerpt = source_excerpt[:max(0, max_chars - len(policy) - 40)]

    if source_excerpt:
        return f"{policy}\nAutoresearch context: {source_excerpt}"
    return policy
