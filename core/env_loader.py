from pathlib import Path
import os


_ENV_LOADED = False


def _parse_env_line(line):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None, None

    if "=" not in stripped:
        return None, None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        return None, None

    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]

    return key, value


def _apply_aliases():
    aliases = {
        "MOUSEMAX_LICENSE": "MOUSEMUX_LICENSE",
        "MOUSEMAX_ENABLE": "MOUSEMUX_ENABLE",
        "MOUSEMAX_AGENT_UID": "MOUSEMUX_AGENT_UID",
    }
    for source_key, target_key in aliases.items():
        source_value = os.environ.get(source_key)
        if source_value and target_key not in os.environ:
            os.environ[target_key] = source_value


def load_env(force=False):
    global _ENV_LOADED

    if _ENV_LOADED and not force:
        return

    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        try:
            for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                key, value = _parse_env_line(raw_line)
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            pass

    _apply_aliases()
    _ENV_LOADED = True
