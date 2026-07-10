import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional

import requests


_DEFAULT_PORT = int(str(os.environ.get("ELI_TEMPEST_PORT", "3333")).strip() or "3333")
_DEFAULT_BASE_URL = str(os.environ.get("ELI_TEMPEST_URL", f"http://127.0.0.1:{_DEFAULT_PORT}")).rstrip("/")
_SERVER_START_TIMEOUT_SECONDS = int(str(os.environ.get("ELI_TEMPEST_START_TIMEOUT", "35")).strip() or "35")

_SERVER_LOCK = threading.Lock()
_SERVER_PROCESS: Optional[subprocess.Popen] = None


def _tempest_root() -> Path:
    env_value = str(os.environ.get("ELI_TEMPEST_DIR", "")).strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (Path(__file__).resolve().parent / "third_party" / "T3MP3ST-main").resolve()


def _healthcheck(base_url: str, timeout_seconds: int = 4) -> bool:
    try:
        response = requests.get(f"{base_url}/api/health", timeout=timeout_seconds)
        return response.ok
    except requests.RequestException:
        return False


def _run_npm_command(args, timeout_seconds: int = 900) -> Dict[str, str]:
    root = _tempest_root()
    if not (root / "package.json").exists():
        raise RuntimeError(f"T3MP3ST source not found at: {root}")

    completed = subprocess.run(
        ["npm", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return {
        "ok": str(completed.returncode == 0),
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
        "code": str(completed.returncode),
    }


def ensure_tempest_installed() -> None:
    root = _tempest_root()
    if not (root / "package.json").exists():
        raise RuntimeError(f"T3MP3ST source not found at: {root}")

    node_modules = root / "node_modules"
    dist_server = root / "dist" / "server.js"

    if not node_modules.exists():
        install = _run_npm_command(["install"])
        if install["ok"] != "True":
            detail = install["stderr"].strip() or install["stdout"].strip() or "npm install failed"
            raise RuntimeError(detail)

    if not dist_server.exists():
        build = _run_npm_command(["run", "build"])
        if build["ok"] != "True":
            detail = build["stderr"].strip() or build["stdout"].strip() or "npm run build failed"
            raise RuntimeError(detail)


def ensure_tempest_server(base_url: str = _DEFAULT_BASE_URL) -> None:
    global _SERVER_PROCESS

    if _healthcheck(base_url):
        return

    with _SERVER_LOCK:
        if _healthcheck(base_url):
            return

        ensure_tempest_installed()

        if _SERVER_PROCESS and _SERVER_PROCESS.poll() is None:
            return

        root = _tempest_root()
        _SERVER_PROCESS = subprocess.Popen(
            ["npm", "run", "server:prod"],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

    deadline = time.time() + _SERVER_START_TIMEOUT_SECONDS
    while time.time() < deadline:
        if _healthcheck(base_url):
            return
        time.sleep(1.0)

    raise RuntimeError("T3MP3ST server did not become healthy in time.")


def _resolve_default_model() -> str:
    return str(os.environ.get("ELI_TEMPEST_MODEL", "anthropic/claude-sonnet-4")).strip() or "anthropic/claude-sonnet-4"


def _resolve_default_provider() -> str:
    return str(os.environ.get("ELI_TEMPEST_PROVIDER", "openrouter")).strip() or "openrouter"


def _resolve_api_key() -> str:
    for key_name in ("ELI_TEMPEST_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        value = str(os.environ.get(key_name, "")).strip()
        if value:
            return value
    return ""


def dispatch_tempest_prompt(objective: str) -> str:
    objective_text = str(objective or "").strip()
    if not objective_text:
        return "Tempest objective was empty."

    base_url = _DEFAULT_BASE_URL
    ensure_tempest_server(base_url=base_url)

    payload = {
        "objective": objective_text,
        "provider": _resolve_default_provider(),
        "model": _resolve_default_model(),
    }

    api_key = _resolve_api_key()
    if api_key:
        payload["apiKey"] = api_key

    try:
        response = requests.post(f"{base_url}/api/general/auto", json=payload, timeout=180)
    except requests.RequestException as exc:
        raise RuntimeError(f"Tempest request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = ""
        try:
            detail_json = response.json()
            detail = detail_json.get("error") or detail_json.get("message") or json.dumps(detail_json)
        except ValueError:
            detail = response.text.strip()
        raise RuntimeError(f"Tempest API error ({response.status_code}): {detail}")

    data = response.json()
    mission_name = str(data.get("missionName") or data.get("codename") or "Unnamed mission")
    operators = data.get("operators") if isinstance(data.get("operators"), list) else []
    targets = data.get("targets") if isinstance(data.get("targets"), list) else []

    return (
        f"Tempest mission started: {mission_name}. "
        f"Operators: {len(operators)}. Targets: {len(targets)}."
    )
