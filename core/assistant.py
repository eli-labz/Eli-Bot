import customtkinter as Ctk
from PIL import Image
import time
import random
import os
import json
from collections import Counter
import subprocess
import shutil
import shlex
import pyautogui
from queue import Queue
import speech_recognition as sr
import threading
import re
from datetime import datetime
from urllib.parse import urlencode, quote_plus
from env_loader import load_env
from assistant_intents import get_word_workflow_steps
from voice import speaker, set_volume, set_subtitles
from driver import assistant, fast_act, auto_role, perform_simulated_keypress, write_action
from tempest_bridge import dispatch_tempest_prompt
from window_focus import activate_windowt_title
from window_focus import heal_and_open_url_in_edge
from window_focus import find_window_by_title, bring_to_foreground
from window_focus import open_windows_info
from core_api import api_call
from human_brain import HumanBrain


load_env()

# Persistent conversational memory (survives app restarts).
CONVERSATION_MAX_STORED_MESSAGES = 120
CONVERSATION_CONTEXT_MESSAGES = 16
CONVERSATION_MEMORY_PATH = os.path.join(
    os.environ.get("ELI_CONVERSATION_DIR", os.path.join(os.path.expanduser("~"), ".eli_bot")),
    "conversation_history.json",
)
chat_history = []
chat_history_lock = threading.Lock()


def _load_chat_history():
    if not os.path.exists(CONVERSATION_MEMORY_PATH):
        return []
    try:
        with open(CONVERSATION_MEMORY_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            messages = payload.get("messages", [])
        else:
            messages = payload
        if not isinstance(messages, list):
            return []
        sanitized = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                sanitized.append({"role": role, "content": content})
        return sanitized[-CONVERSATION_MAX_STORED_MESSAGES:]
    except Exception as e:
        print(f"Failed to load conversation memory: {e}")
        return []


def _save_chat_history(history):
    try:
        os.makedirs(os.path.dirname(CONVERSATION_MEMORY_PATH), exist_ok=True)
        with open(CONVERSATION_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({"messages": history[-CONVERSATION_MAX_STORED_MESSAGES:]}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save conversation memory: {e}")


def _clear_chat_history():
    global chat_history
    with chat_history_lock:
        chat_history = []
    try:
        if os.path.exists(CONVERSATION_MEMORY_PATH):
            os.remove(CONVERSATION_MEMORY_PATH)
    except Exception as e:
        print(f"Failed to clear conversation memory: {e}")


chat_history = _load_chat_history()
TEMPEST_STRICT_ENV = "ELI_TEMPEST_STRICT_MODE"
HUMAN_BRAIN = HumanBrain()


def _reload_human_brain() -> None:
    global HUMAN_BRAIN
    HUMAN_BRAIN = HumanBrain()


def _format_brain_status_summary() -> str:
    snapshot = HUMAN_BRAIN.all_domain_snapshots()
    domains = snapshot.get("domains", {})
    parts = []
    for domain_name in ("chat", "tasks", "finance"):
        domain = domains.get(domain_name, {})
        if not isinstance(domain, dict):
            continue
        level = domain.get("consciousness_level", {}) if isinstance(domain.get("consciousness_level"), dict) else {}
        level_id = int(level.get("level", -1))
        level_name = str(level.get("name", "Unknown"))
        parts.append(
            f"{domain_name}: val={domain.get('valence', 0.0):.2f}, "
            f"aro={domain.get('arousal', 0.0):.2f}, "
            f"focus={domain.get('focus', 0.0):.2f}, "
            f"updates={int(domain.get('updates', 0))}, "
            f"L{level_id}:{level_name}"
        )

    return (
        f"Brain status | profile={snapshot.get('profile')} | "
        f"decay={'on' if snapshot.get('decay_enabled') else 'off'} "
        f"(half_life={snapshot.get('decay_half_life_seconds')}) | "
        + " ; ".join(parts)
    )


def _summarize_brain_mistakes(limit: int = 10) -> str:
    safe_limit = max(1, min(100, int(limit or 10)))
    trace_dir = os.path.abspath(os.environ.get("ELI_EDGE_ACTIONS_TRACE_DIR", "edge_action_traces"))
    if not os.path.isdir(trace_dir):
        return f"No trace directory found at {trace_dir}. Run an edge task first."

    try:
        files = [
            os.path.join(trace_dir, name)
            for name in os.listdir(trace_dir)
            if name.lower().endswith(".json")
        ]
    except Exception as e:
        return f"Unable to read trace directory: {e}"

    if not files:
        return f"No trace files found in {trace_dir}."

    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    mistakes = []
    pattern_counter = Counter()

    for path in files:
        try:
            payload = json.loads(open(path, "r", encoding="utf-8").read())
        except Exception:
            continue

        events = payload.get("events", []) if isinstance(payload, dict) else []
        task_id = str(payload.get("task_id", "unknown")) if isinstance(payload, dict) else "unknown"

        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "consequence_assessment":
                continue
            if not bool(event.get("unintended", False)):
                continue

            severity = str(event.get("severity", "unknown"))
            summary = str(event.get("summary", "unknown consequence"))
            step = int(event.get("step", -1))
            stamp = str(event.get("timestamp", ""))
            recommendation = str(event.get("recommended_recovery", "none"))

            mistakes.append(
                {
                    "task": task_id,
                    "step": step,
                    "severity": severity,
                    "summary": summary,
                    "timestamp": stamp,
                    "recommended_recovery": recommendation,
                }
            )
            pattern_counter[summary] += 1

    if not mistakes:
        return "No unintended consequence events found in current traces."

    # Most recent first by timestamp string (ISO) then insertion order fallback.
    mistakes.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
    recent = mistakes[:safe_limit]

    recent_text = " | ".join(
        f"{m.get('task')}#s{m.get('step')}:{m.get('severity')}:{m.get('summary')}"
        for m in recent
    )

    severity_counts = Counter()
    for item in recent:
        level = str(item.get("severity", "other")).strip().lower()
        if level not in {"high", "medium", "low"}:
            level = "other"
        severity_counts[level] += 1

    severity_text = (
        f"high={severity_counts.get('high', 0)}, "
        f"medium={severity_counts.get('medium', 0)}, "
        f"low={severity_counts.get('low', 0)}, "
        f"other={severity_counts.get('other', 0)}"
    )

    top_patterns = pattern_counter.most_common(3)
    pattern_text = " | ".join(f"{summary} x{count}" for summary, count in top_patterns)

    return (
        f"Brain mistakes summary (last {len(recent)} unintended events). "
        f"Severity buckets: {severity_text}. "
        f"Recent: {recent_text}. "
        f"Top patterns: {pattern_text}."
    )


def _apply_brain_preset_env(preset: str) -> bool:
    normalized = str(preset or "").strip().lower()
    if normalized not in {"cautious", "balanced", "aggressive"}:
        return False

    if normalized == "cautious":
        updates = {
            "ELI_HUMAN_BRAIN_PROFILE": "cautious",
            "ELI_HUMAN_BRAIN_DECAY_HALF_LIFE_SECONDS": "1200",
            "ELI_BRAIN_PLANNER_MAX_COGNITIVE_GUARDS": "4",
            "ELI_BRAIN_PLANNER_HIGH_AROUSAL_THRESHOLD": "0.5",
            "ELI_BRAIN_RISK_HIGH_AROUSAL_THRESHOLD": "0.55",
            "ELI_BRAIN_RISK_LOW_FOCUS_THRESHOLD": "0.45",
        }
    elif normalized == "aggressive":
        updates = {
            "ELI_HUMAN_BRAIN_PROFILE": "aggressive",
            "ELI_HUMAN_BRAIN_DECAY_HALF_LIFE_SECONDS": "600",
            "ELI_BRAIN_PLANNER_MAX_COGNITIVE_GUARDS": "1",
            "ELI_BRAIN_PLANNER_HIGH_AROUSAL_THRESHOLD": "0.85",
            "ELI_BRAIN_RISK_HIGH_AROUSAL_THRESHOLD": "0.9",
            "ELI_BRAIN_RISK_LOW_FOCUS_THRESHOLD": "0.15",
        }
    else:
        updates = {
            "ELI_HUMAN_BRAIN_PROFILE": "balanced",
            "ELI_HUMAN_BRAIN_DECAY_HALF_LIFE_SECONDS": "900",
            "ELI_BRAIN_PLANNER_MAX_COGNITIVE_GUARDS": "2",
            "ELI_BRAIN_PLANNER_HIGH_AROUSAL_THRESHOLD": "0.65",
            "ELI_BRAIN_RISK_HIGH_AROUSAL_THRESHOLD": "0.7",
            "ELI_BRAIN_RISK_LOW_FOCUS_THRESHOLD": "0.3",
        }

    for key, value in updates.items():
        os.environ[key] = value

    _reload_human_brain()
    return True


def _is_tempest_strict_mode_enabled() -> bool:
    return str(os.environ.get(TEMPEST_STRICT_ENV, "")).strip().lower() in {"1", "true", "yes", "on"}


def _set_tempest_strict_mode(enabled: bool) -> None:
    os.environ[TEMPEST_STRICT_ENV] = "1" if enabled else "0"


def generate_conversational_response(user_message):
    global chat_history
    text = str(user_message or "").strip()
    if not text:
        return "Tell me anything and I'll keep the conversation going."

    normalized = text.lower()
    if normalized in {"reset chat", "clear chat", "forget conversation", "new conversation"}:
        _clear_chat_history()
        return "Conversation memory cleared. Starting fresh."

    brain_context = HUMAN_BRAIN.build_prompt_context(text, domain="chat")

    system_prompt = (
        "You are Eli Bot, a helpful, joyful, and friendly Conversational AI. "
        "Keep your responses relatively brief, friendly, and natural. "
        "Do not output markdown code blocks unless requested. Avoid technical jargon unless asked. "
        "Treat this as an ongoing conversation: keep continuity with prior context and resolve references like pronouns naturally. "
        f"{brain_context}"
    )

    with chat_history_lock:
        chat_history = chat_history[-CONVERSATION_MAX_STORED_MESSAGES:]
        history_context = chat_history[-CONVERSATION_CONTEXT_MESSAGES:]

    messages = [{"role": "system", "content": system_prompt}, *history_context, {"role": "user", "content": text}]

    try:
        response = api_call(messages, max_tokens=200, temperature=0.7)
    except Exception as e:
        print(f"Error in api_call for conversation: {e}")
        response = "I'm sorry, I'm having trouble thinking right now."

    with chat_history_lock:
        chat_history.append({"role": "user", "content": text})
        chat_history.append({"role": "assistant", "content": response})
        chat_history = chat_history[-CONVERSATION_MAX_STORED_MESSAGES:]
        _save_chat_history(chat_history)

    return response

# Initialize the speech recognition and text to speech engines
assistant_voice_recognition_enabled = True  # Disable if you don't want to use voice recognition
assistant_name_handle = "Ok Computer"  # Change this to your preferred name, will be used for voice activation.
assistant_anim_enabled = True
assistant_voice_enabled = True
set_volume(0.25)
assistant_subtitles_enabled = True
recognizer = sr.Recognizer()
message_queue = Queue()
Ctk.set_appearance_mode("dark")  # Modes: system (default), light, dark
Ctk.set_default_color_theme("dark-blue")  # Themes: blue (default), dark-blue, green


def listen_to_speech():
    # Function to listen for speech and add the recognized text to the message queue
    with sr.Microphone() as source:
        try:
            print("Assistant Listening...")
            audio = recognizer.listen(source, timeout=5)  # Listen for 5 seconds
            message = recognizer.recognize_google(audio)
            print("You said:", message)
            message_queue.put(message)
            return message
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))
        except sr.WaitTimeoutError:
            print("Listening timed out.")
        finally:
            # Schedule the function to be called again
            # root.after(1000, listen_to_speech) # This if you want to try it indefinitely.
            print("Google Speech Recognition could not understand audio")
            pass


def process_queue():
    # Function to check the message queue and show messages as bubbles
    try:
        while not message_queue.empty():
            message = message_queue.get_nowait()
            if message:
                show_message(None, message)  # Pass None for event
                speaker(message)
    finally:
        # Schedule the function to be called again
        root.after(100, process_queue)
        pass


def on_drag(event):
    # Function to move the window on drag
    global is_dragging, position_right, position_bottom, drag_time
    drag_time = time.time()
    is_dragging = True
    x = root.winfo_pointerx() - offset_x
    y = root.winfo_pointery() - offset_y
    root.geometry(f'+{x}+{y}')
    label.configure(image=assistant_dragging_photo)


def end_drag(event):
    global is_dragging, position_right, position_bottom, drag_time, click_time
    if not click_time:
        return
    dragged_message = "Whats the action?" if time.time() - click_time < 0.15 else "You dragged me!"
    # If the duration of the drag is less than the threshold for a click
    if time.time() - drag_time < 0.15:
        is_dragging = False
        position_right = root.winfo_x()
        position_bottom = root.winfo_y()
        label.configure(image=assistant_photo)
        animate_move()
        create_input_bubble(action=True)
    else:
        label.configure(image=assistant_photo)
        animate_move()  # Resume the movement animation
        create_input_bubble(action=True)
    print(f"Clicked on the assistant: {dragged_message}")


def create_input_bubble(action=False):
    # Get dimensions for proper placement
    bubble_width = 450  # Set a fixed width for the bubble
    bubble_height = 28  # A reasonable height to fit the text entry
    # Calculate the bubble position to the left of the assistant
    bubble_x = root.winfo_x() - bubble_width + 40  # Adjust the X position as needed
    bubble_y = root.winfo_y() + (assistant_photo_height // 2) - (bubble_height // 2) + 40
    # Create bubble as a top-level window
    bubble = Ctk.CTkToplevel(root)
    bubble.attributes('-alpha', 0.85)
    bubble.overrideredirect(True)
    bubble.attributes('-topmost', True)
    bubble.geometry(f'{bubble_width}x{bubble_height}+{bubble_x}+{bubble_y}')

    def _close_bubble(_event=None):
        try:
            bubble.grab_release()
        except Ctk.ctk_tk.TclError:
            pass
        bubble.destroy()

    bubble.bind("<Escape>", _close_bubble)
    # Create the entry widget
    entry = Ctk.CTkEntry(bubble, corner_radius=6, placeholder_text_color="#0b2d39",
                         fg_color="#e1f2f1", text_color="#040f13",
                         placeholder_text="Type action or chat here...", width=450,
                         border_width=1, border_color="darkgray")
    entry.bind("<Escape>", _close_bubble)
    entry.pack(padx=0, pady=0)

    try:
        bubble.grab_set()
    except Ctk.ctk_tk.TclError:
        pass
    # Force focus on the entry and bubble
    try:
        bubble.after(10, lambda: [bubble.lift(), bubble.focus_force(), entry.focus_force()])
    except Ctk.ctk_tk.TclError:
        # Ignore the error, as the window or widget is no longer valid
        pass
    # Bind Return and Escape keys to process input or destroy bubble
    entry.bind("<Return>", lambda e: process_input_and_close(bubble, entry, action))
    # Bind mouse click to focus back on entry
    bubble.bind("<Button-1>", lambda e: entry.focus_force())
    # Make sure bubble is focused as well when clicking on it
    bubble.bind("<FocusIn>", lambda e: entry.focus_force())
    return bubble  # Returning bubble reference in case it needs to be accessed


def _looks_like_action_request(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False

    normalized = raw.lower()
    action_prefixes = (
        "open ", "launch ", "click ", "click on ", "double click ", "right click ",
        "press ", "type ", "write ", "scroll", "run ", "execute ", "start ",
        "close ", "switch ", "move ", "drag ", "drop ", "save ", "export ",
        "search ", "find ", "book ", "plan ", "word ", "winword ", "edge task ",
        "browser task ", "bash:", "bash ", "shell:", "shell ",
    )

    if normalized.startswith(action_prefixes):
        return True

    if re.match(r"^(https?://|www\.)\S+$", raw, flags=re.IGNORECASE):
        return True

    if re.match(r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)+(?:/\S*)?$", raw, flags=re.IGNORECASE):
        return True

    return False


def _prefer_conversation(text: str, action_mode: bool = False) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False

    normalized = raw.lower()
    greeting_pattern = re.compile(
        r"^(hi|hello|hey|yo|good\s+(morning|afternoon|evening)|how are you|what's up|whats up)\b",
        flags=re.IGNORECASE,
    )
    if greeting_pattern.search(normalized):
        return True

    # In action mode, only keep action routing when the user actually typed an actionable command.
    if action_mode and _looks_like_action_request(raw):
        return False

    if _looks_like_action_request(raw):
        return False

    # Natural dialogue cues: questions and short free-form statements with no action verbs.
    if raw.endswith("?") or len(raw.split()) <= 8:
        return True

    return False


def _extract_forced_computer_use_goal(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    normalized = raw.lower()
    trigger_phrases = (
        "brute force computer use",
        "force computer use",
        "computer use brute force",
        "computer use",
        "force agent",
    )
    if not any(phrase in normalized for phrase in trigger_phrases):
        return ""

    # Keep the user objective by stripping common force-control tokens.
    goal = re.sub(
        r"\b(brute\s*force|force|computer\s*use|agent|for|to|the)\b",
        " ",
        raw,
        flags=re.IGNORECASE,
    )
    goal = re.sub(r"\s+", " ", goal).strip(" .:-")
    return goal or raw


def _is_forced_computer_use_command(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw.startswith("/"):
        return False

    body = raw[1:].strip()
    if not body:
        return False

    cmd = body.split(" ", 1)[0].lower().strip()
    return cmd in {"computer", "computeruse", "cu", "force"}


def _show_computer_use_forced_badge(bubble, entry):
    try:
        bubble.configure(fg_color="#12311f")
    except Exception:
        pass

    try:
        entry.configure(border_color="#2fd46f", border_width=2)
    except Exception:
        pass

    try:
        badge = Ctk.CTkLabel(
            bubble,
            text="Computer Use forced",
            fg_color="#2fd46f",
            text_color="#062112",
            corner_radius=8,
            padx=8,
            pady=1,
            font=("Segoe UI", 10, "bold"),
        )
        badge.place(relx=1.0, x=-8, y=2, anchor="ne")
    except Exception:
        pass


def _handle_slash_command(text: str, action_mode: bool = False) -> bool:
    raw = str(text or "").strip()
    if not raw.startswith("/"):
        return False

    body = raw[1:].strip()
    if not body:
        message_queue.put("Empty slash command. Use /help.")
        return True

    parts = body.split(" ", 1)
    cmd = parts[0].lower().strip()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"help", "?"}:
        message_queue.put(
            "Slash commands: /help, /chat <text>, /action <step>, /assistant <goal>, /word <instruction>, /tempest <objective>, /tempest-strict <on|off|status>, /brain-status [domain|levels|trend [domain]|mistakes [N]|profile <mode>|preset <cautious|balanced|aggressive>|set <ENV_KEY> <value>|decay [domain]], /clear"
        )
        return True

    if cmd in {"brain-status", "brain", "brainstatus"}:
        if arg.lower().strip().startswith("mistakes"):
            parts_mistakes = arg.split(" ", 1)
            if len(parts_mistakes) > 1 and parts_mistakes[1].strip():
                try:
                    n = int(parts_mistakes[1].strip())
                except Exception:
                    message_queue.put("Usage: /brain-status mistakes [N]")
                    return True
            else:
                n = 10
            message_queue.put(_summarize_brain_mistakes(n))
            return True

        if arg.lower().strip().startswith("levels"):
            message_queue.put(HUMAN_BRAIN.consciousness_catalog_summary())
            return True

        if not arg or arg.lower().strip() in {"status", "show", "all"}:
            message_queue.put(_format_brain_status_summary())
            return True

        lowered = arg.lower().strip()
        if lowered.startswith("profile "):
            profile = arg.split(" ", 1)[1].strip().lower()
            if profile not in {"cautious", "balanced", "aggressive"}:
                message_queue.put("Usage: /brain-status profile <cautious|balanced|aggressive>")
                return True
            os.environ["ELI_HUMAN_BRAIN_PROFILE"] = profile
            _reload_human_brain()
            message_queue.put(f"Brain profile updated to {profile}.")
            message_queue.put(_format_brain_status_summary())
            return True

        if lowered.startswith("preset "):
            preset = arg.split(" ", 1)[1].strip().lower()
            if not _apply_brain_preset_env(preset):
                message_queue.put("Usage: /brain-status preset <cautious|balanced|aggressive>")
                return True
            message_queue.put(f"Brain preset applied: {preset}")
            message_queue.put(_format_brain_status_summary())
            return True

        if lowered.startswith("set "):
            set_parts = arg.split(" ", 2)
            if len(set_parts) < 3:
                message_queue.put("Usage: /brain-status set <ENV_KEY> <value>")
                return True
            key = set_parts[1].strip()
            value = set_parts[2].strip()
            if not key.startswith("ELI_HUMAN_BRAIN_") and not key.startswith("ELI_BRAIN_"):
                message_queue.put("Only ELI_HUMAN_BRAIN_* or ELI_BRAIN_* keys are allowed.")
                return True
            os.environ[key] = value
            _reload_human_brain()
            message_queue.put(f"Brain setting updated: {key}={value}")
            message_queue.put(_format_brain_status_summary())
            return True

        if lowered.startswith("decay"):
            parts_decay = arg.split(" ", 1)
            domain = parts_decay[1].strip().lower() if len(parts_decay) > 1 else "chat"
            snap = HUMAN_BRAIN.decay_now(domain)
            message_queue.put(
                f"Decay applied for {snap.get('domain')}: val={snap.get('valence', 0.0):.2f}, "
                f"aro={snap.get('arousal', 0.0):.2f}, focus={snap.get('focus', 0.0):.2f}"
            )
            return True

        if lowered.startswith("trend"):
            parts_trend = arg.split(" ", 1)
            domain = parts_trend[1].strip().lower() if len(parts_trend) > 1 else "chat"
            trend = HUMAN_BRAIN.trend_snapshot(domain)
            delta = trend.get("delta", {}) if isinstance(trend.get("delta"), dict) else {}
            message_queue.put(
                f"Brain trend {trend.get('domain')}: samples={int(trend.get('samples', 0))}, "
                f"d_focus={float(delta.get('focus', 0.0)):.3f}, "
                f"d_arousal={float(delta.get('arousal', 0.0)):.3f}, "
                f"d_valence={float(delta.get('valence', 0.0)):.3f}"
            )
            return True

        # Treat free-form arg as a domain selector.
        domain_snapshot = HUMAN_BRAIN.state_snapshot(arg.lower().strip())
        level = domain_snapshot.get("consciousness_level", {}) if isinstance(domain_snapshot.get("consciousness_level"), dict) else {}
        message_queue.put(
            f"Brain domain {domain_snapshot.get('domain')}: profile={domain_snapshot.get('profile')}, "
            f"val={domain_snapshot.get('valence', 0.0):.2f}, aro={domain_snapshot.get('arousal', 0.0):.2f}, "
            f"focus={domain_snapshot.get('focus', 0.0):.2f}, updates={int(domain_snapshot.get('updates', 0))}, "
            f"L{int(level.get('level', -1))}:{str(level.get('name', 'Unknown'))}"
        )
        return True

    if cmd in {"tempest-strict", "strict", "failfast"}:
        setting = arg.lower().strip()
        if not setting or setting in {"status", "state"}:
            status = "ON" if _is_tempest_strict_mode_enabled() else "OFF"
            message_queue.put(f"Tempest strict mode: {status}")
            return True
        if setting in {"on", "enable", "enabled", "true", "1"}:
            _set_tempest_strict_mode(True)
            message_queue.put("Tempest strict mode enabled. Only T3MP3ST actions will run; local fallback is disabled.")
            return True
        if setting in {"off", "disable", "disabled", "false", "0"}:
            _set_tempest_strict_mode(False)
            message_queue.put("Tempest strict mode disabled. Local fallback is enabled.")
            return True
        message_queue.put("Usage: /tempest-strict <on|off|status>")
        return True

    if cmd in {"clear", "reset", "forget"}:
        _clear_chat_history()
        message_queue.put("Conversation memory cleared.")
        return True

    if cmd == "chat":
        if not arg:
            message_queue.put("Usage: /chat <message>")
            return True
        response = generate_conversational_response(arg)
        message_queue.put(response)
        return True

    if cmd in {"action", "act"}:
        if not arg:
            message_queue.put("Usage: /action <step>")
            return True
        run_fast_action(arg)
        return True

    if cmd in {"assistant", "plan"}:
        if not arg:
            message_queue.put("Usage: /assistant <goal>")
            return True
        run_assistant(arg)
        return True

    if cmd == "word":
        if not arg:
            message_queue.put("Usage: /word <instruction>")
            return True
        instruction = arg if arg.lower().startswith(("word ", "winword ")) else f"word {arg}"
        run_fast_action(instruction)
        return True

    if cmd in {"tempest", "t3mp3st"}:
        if not arg:
            message_queue.put("Usage: /tempest <objective>")
            return True
        run_tempest_action(arg)
        return True

    if cmd in {"computer", "computeruse", "cu", "force"}:
        if not arg:
            message_queue.put("Usage: /computer <objective>")
            return True
        run_fast_action(arg)
        return True

    if cmd in {"mode", "state"}:
        mode_label = "action" if action_mode else "chat"
        message_queue.put(f"Input mode: {mode_label}")
        return True

    message_queue.put(f"Unknown slash command: /{cmd}. Use /help.")
    return True

def process_input_and_close(bubble, entry, action=False):
    user_input = entry.get()
    print(f"Processing input: {user_input}")
    text = user_input.strip()
    forced_goal = _extract_forced_computer_use_goal(text)
    force_command = _is_forced_computer_use_command(text)
    force_badge_enabled = bool(forced_goal or force_command)

    bubble_closed = False

    def _destroy_bubble():
        nonlocal bubble_closed
        if bubble_closed:
            return
        try:
            bubble.grab_release()
        except Ctk.ctk_tk.TclError:
            pass
        try:
            bubble.destroy()
        except Ctk.ctk_tk.TclError:
            pass
        bubble_closed = True

    if text:
        if force_badge_enabled:
            _show_computer_use_forced_badge(bubble, entry)
            try:
                bubble.after(900, _destroy_bubble)
            except Ctk.ctk_tk.TclError:
                _destroy_bubble()
        else:
            _destroy_bubble()

        # Use the user input as needed: display, speech, or further processing.
        show_message(None, text)
        
        def handle_input_thread(text, forced_override=""):
            if _handle_slash_command(text, action_mode=action):
                return

            if forced_override:
                run_fast_action(forced_override)
                return

            # Hard-route travel booking intents to action automation so prompts like
            # "Book me a flight ..." don't get diverted into chat/classifier paths.
            if _looks_like_expedia_trip_request(text.lower()):
                run_fast_action(text)
                return

            if _prefer_conversation(text, action_mode=action):
                response = generate_conversational_response(text)
                message_queue.put(response)
                return

            role_function = auto_role(text)
            print(f"Input Role Selection: {role_function}")
            if "joyful_conversation" in role_function:
                response = generate_conversational_response(text)
                message_queue.put(response)
            elif "windows_assistant" in role_function:
                if action:
                    print("Performing action: ", text)
                    run_fast_action(text)
                else:
                    print(f"Running assistant... Generating test case: {text}")
                    speaker(f"Running assistant... Generating test case: {text}")
                    run_assistant(text)
            else:
                # Fallback to conversational response
                response = generate_conversational_response(text)
                message_queue.put(response)

        threading.Thread(target=handle_input_thread, args=(text, forced_goal), daemon=True).start()
    else:
        _destroy_bubble()  # Close immediately when there is no input.

def listen_and_respond():
    action = listen_to_speech()
    if action:  # Check if action is not None or empty string
        show_message(None, action)
        # Execute the assistant function in a separate thread
        # assistant_thread = threading.Thread(target=run_assistant, args=(action,))
        # assistant_thread.start()


def run_assistant(action):
    print("Running assistant...")
    assistant(assistant_goal=action, called_from="assistant")


def run_fast_action(action_text):
    print("Running fast action...")
    try:
        _run_bruteforce_action(action_text)
    except Exception as e:
        print(f"Fast action failed: {e}")
        message_queue.put("Action failed. Check console logs.")


def run_tempest_action(action_text):
    objective = str(action_text or "").strip()
    if not objective:
        message_queue.put("Tempest objective was empty.")
        return False

    try:
        result_message = dispatch_tempest_prompt(objective)
    except Exception as e:
        print(f"Tempest dispatch failed: {e}")
        message_queue.put(f"Tempest failed: {e}")
        return False

    message_queue.put(result_message)
    return True


def _attempt_tempest_first(raw_action: str) -> bool:
    objective = str(raw_action or "").strip()
    if not objective:
        return False

    # Hard-route each action through T3MP3ST first, then fall back to local execution only on failure.
    return bool(run_tempest_action(objective))


def _run_bruteforce_action(action_text):
    raw = str(action_text or "").strip()
    if not raw:
        return

    normalized = raw.lower()
    explicit_tempest = normalized.startswith("tempest ") or normalized.startswith("t3mp3st ")
    tempest_objective = raw.split(" ", 1)[1].strip() if explicit_tempest and " " in raw else raw

    if _attempt_tempest_first(tempest_objective):
        return

    if _is_tempest_strict_mode_enabled():
        message_queue.put("Tempest strict mode blocked local fallback because T3MP3ST did not complete the action.")
        return

    if explicit_tempest:
        return

    if _try_autoresearch_word_actions(raw):
        return

    if _try_word_actions(raw):
        return

    if _try_edge_actions(raw):
        return

    bash_command = _extract_bash_command(raw)
    if bash_command:
        _execute_bash_command(bash_command)
        return

    if _try_launch_exe_from_prompt(raw):
        return

    if _looks_like_expedia_trip_request(normalized):
        if _plan_trip_on_expedia(raw):
            return

    if re.match(r"^(https?://|www\.)\S+$", raw, flags=re.IGNORECASE) or re.match(
        r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)+(?:/\S*)?$", raw, flags=re.IGNORECASE
    ):
        _execute_any_url_end_to_end(raw, f"Open this URL and complete the requested objective end-to-end: {raw}")
        return

    extracted_url = _extract_any_url_from_text(raw)
    if extracted_url:
        _execute_any_url_end_to_end(extracted_url, raw)
        return

    workflow_steps = get_word_workflow_steps(raw)
    if workflow_steps:
        for step in workflow_steps:
            _try_word_actions(step)
        return

    # Direct command families first: deterministic and fast.
    if normalized.startswith("open ") or normalized.startswith("launch "):
        target = raw.split(" ", 1)[1].strip() if " " in raw else raw
        activate_windowt_title(target)
        return

    if normalized.startswith("press "):
        perform_simulated_keypress(raw.split(" ", 1)[1].strip())
        return

    if normalized.startswith("type ") or normalized.startswith("write "):
        payload = raw.split(" ", 1)[1].strip() if " " in raw else ""
        if payload:
            write_action(goal=payload, last_step="text_entry")
        return

    if normalized.startswith("scroll"):
        import pyautogui
        pyautogui.scroll(-850)
        return

    # Brute-force click-oriented execution paths.
    attempts = [
        {"double_click": False, "right_click": False},
        {"double_click": True, "right_click": False},
        {"double_click": False, "right_click": True},
    ]

    for idx, attempt in enumerate(attempts, start=1):
        try:
            print(f"Brute-force attempt {idx}: {attempt}")
            result = fast_act(
                single_step=raw,
                double_click=attempt["double_click"],
                right_click=attempt["right_click"],
            )
            if result:
                return
        except Exception as e:
            print(f"Brute-force attempt {idx} failed: {e}")

    # Last fallback: let full planner generate a recoverable multi-step sequence.
    print("Brute-force fallback: escalating to assistant planner")
    assistant(assistant_goal=raw, called_from="assistant")


def _try_launch_exe_from_prompt(prompt: str) -> bool:
    text = str(prompt or "").strip()
    if not text:
        return False

    lowered = text.lower()
    prefixes = ("open ", "launch ", "run ", "execute ", "start ")
    prefixed = False
    payload = text

    for prefix in prefixes:
        if lowered.startswith(prefix):
            prefixed = True
            payload = text[len(prefix):].strip()
            break

    if not prefixed and ".exe" not in lowered:
        return False

    if not payload:
        message_queue.put("No executable path provided.")
        return True

    raw_exe = ""
    args = []

    quoted_match = re.search(r"[\"']([^\"']+?\.exe)[\"']", payload, flags=re.IGNORECASE)
    if quoted_match:
        raw_exe = quoted_match.group(1).strip()
        remainder = (payload[:quoted_match.start()] + payload[quoted_match.end():]).strip()
        if remainder:
            try:
                args = [part.strip() for part in shlex.split(remainder, posix=False)]
            except ValueError:
                args = [remainder]
    else:
        try:
            tokens = shlex.split(payload, posix=False)
        except ValueError:
            tokens = [payload]

        if not tokens:
            message_queue.put("No executable path provided.")
            return True

        exe_index = -1
        for idx, token in enumerate(tokens):
            clean = token.strip().strip('"').strip("'")
            if clean.lower().endswith(".exe"):
                exe_index = idx
                break

        if exe_index >= 0:
            raw_exe = tokens[exe_index].strip().strip('"').strip("'")
            args = [part.strip() for part in tokens[exe_index + 1 :]]
        elif prefixed:
            raw_exe = tokens[0].strip().strip('"').strip("'")
            args = [part.strip() for part in tokens[1:]]
        else:
            return False

    if not raw_exe:
        message_queue.put("No executable path provided.")
        return True

    resolved_exe = _resolve_exe_from_prompt(raw_exe)
    if not resolved_exe:
        message_queue.put(f"Executable not found: {raw_exe}")
        return True

    launch_cwd = os.path.dirname(resolved_exe) or None
    launch_errors = []

    try:
        subprocess.Popen([resolved_exe, *args], cwd=launch_cwd)
        message_queue.put(f"Launched EXE: {resolved_exe}")
        return True
    except Exception as e:
        launch_errors.append(f"popen={e}")

    try:
        if not args:
            os.startfile(resolved_exe)
            message_queue.put(f"Launched EXE: {resolved_exe}")
            return True
    except Exception as e:
        launch_errors.append(f"startfile={e}")

    try:
        subprocess.Popen(["cmd", "/c", "start", "", resolved_exe, *args], cwd=launch_cwd, shell=False)
        message_queue.put(f"Launched EXE: {resolved_exe}")
        return True
    except Exception as e:
        launch_errors.append(f"cmd_start={e}")

    detail = launch_errors[0] if launch_errors else "unknown error"
    message_queue.put(f"EXE launch failed: {detail}")
    return True


def _resolve_exe_from_prompt(raw_exe: str) -> str:
    exe_candidate = os.path.expandvars(os.path.expanduser(str(raw_exe or "").strip()))
    if not exe_candidate:
        return ""

    candidates = [exe_candidate]
    if not exe_candidate.lower().endswith(".exe"):
        candidates.append(f"{exe_candidate}.exe")

    for candidate in candidates:
        if os.path.isabs(candidate) and os.path.isfile(candidate):
            return candidate

        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

        path_hit = shutil.which(candidate) or shutil.which(os.path.basename(candidate))
        if path_hit:
            return path_hit

    return ""


def _extract_bash_command(raw_action: str) -> str:
    text = str(raw_action or "").strip()
    if not text:
        return ""

    lowered = text.lower()
    prefixes = ("bash:", "bash ", "run bash ", "shell:", "shell ")
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip()
    return ""


def _resolve_git_bash_executable() -> str:
    env_path = str(os.environ.get("ELI_GIT_BASH", "")).strip()
    if env_path and os.path.exists(env_path):
        return env_path

    preferred_paths = (
        "C:\\Program Files\\Git\\bin\\bash.exe",
        "C:\\Program Files\\Git\\git-bash.exe",
        "C:\\ProgramData\\chocolatey\\lib\\git.portable\\tools\\bin\\bash.exe",
        "C:\\ProgramData\\chocolatey\\lib\\git.portable\\tools\\git-bash.exe",
    )
    for path in preferred_paths:
        if os.path.exists(path):
            return path

    for candidate in ("git-bash", "bash"):
        resolved = shutil.which(candidate)
        if resolved and os.path.exists(resolved):
            return resolved
    return ""


def _execute_bash_command(command: str):
    cmd = str(command or "").strip()
    if not cmd:
        message_queue.put("Bash command was empty.")
        return

    if _try_launch_exe_from_bash_command(cmd):
        return

    bash_exe = _resolve_git_bash_executable()
    if not bash_exe:
        message_queue.put("Git Bash not found. Install with: choco install git.portable -y")
        return

    timeout_seconds = int(str(os.environ.get("ELI_BASH_TIMEOUT", "90")).strip() or "90")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    try:
        result = subprocess.run(
            [bash_exe, "-lc", cmd],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        message_queue.put(f"Bash command timed out after {timeout_seconds}s.")
        return
    except Exception as e:
        message_queue.put(f"Bash execution failed: {e}")
        return

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    exit_code = result.returncode

    if stdout:
        print(f"[bash stdout]\n{stdout}")
    if stderr:
        print(f"[bash stderr]\n{stderr}")

    if exit_code == 0:
        summary = stdout[:260] if stdout else "Command finished successfully."
        message_queue.put(f"Bash OK: {summary}")
    else:
        failure = stderr[:260] if stderr else (stdout[:260] if stdout else "Unknown Bash error")
        message_queue.put(f"Bash failed (exit {exit_code}): {failure}")


def _try_launch_exe_from_bash_command(command: str) -> bool:
    text = str(command or "").strip()
    if not text:
        return False

    match = re.match(r"^(?:open-exe|launch-exe|open)\s+(.+)$", text, flags=re.IGNORECASE)
    if not match:
        return False

    payload = match.group(1).strip()
    if not payload:
        message_queue.put("No executable path provided.")
        return True

    try:
        tokens = shlex.split(payload, posix=False)
    except ValueError:
        tokens = [payload]

    if not tokens:
        message_queue.put("No executable path provided.")
        return True

    raw_exe = tokens[0].strip().strip('"').strip("'")
    args = [t.strip() for t in tokens[1:]]

    if not raw_exe.lower().endswith(".exe"):
        message_queue.put("Only .exe launch is supported for open-exe/launch-exe/open.")
        return True

    exe_candidate = os.path.expandvars(os.path.expanduser(raw_exe))
    resolved_exe = ""

    if os.path.isabs(exe_candidate) and os.path.exists(exe_candidate):
        resolved_exe = exe_candidate
    else:
        path_hit = shutil.which(exe_candidate) or shutil.which(os.path.basename(exe_candidate))
        if path_hit:
            resolved_exe = path_hit

    if not resolved_exe:
        message_queue.put(f"Executable not found: {raw_exe}")
        return True

    try:
        launch_cwd = os.path.dirname(resolved_exe) or None
        subprocess.Popen([resolved_exe, *args], cwd=launch_cwd)
        message_queue.put(f"Launched EXE: {resolved_exe}")
    except Exception as e:
        message_queue.put(f"EXE launch failed: {e}")
    return True


def _extract_any_url_from_text(text: str) -> str:
    raw = str(text or "")
    url_pattern = re.compile(
        r"((?:https?://|www\.)[^\s]+|[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+(?:/[^\s]*)?)",
        flags=re.IGNORECASE,
    )
    match = url_pattern.search(raw)
    if not match:
        return ""
    return match.group(1).rstrip(").,;:!?")


def _execute_any_url_end_to_end(url: str, objective_prompt: str) -> bool:
    clean_url = str(url or "").strip().strip('"').strip("'")
    if not clean_url:
        return False

    speaker("Opening URL in Microsoft Edge and executing end-to-end.")
    opened, healed_url = heal_and_open_url_in_edge(clean_url)
    final_url = healed_url or clean_url
    if not opened:
        activate_windowt_title(clean_url)
    time.sleep(1.2)

    assistant(
        assistant_goal=(
            "Control Microsoft Edge end-to-end on this URL: "
            f"{final_url}. "
            f"User objective: {objective_prompt}. "
            "Before each critical step, validate the current URL against the intended domain/path and repair it if malformed. "
            "If URL is malformed or over-encoded, normalize it and re-open the corrected URL immediately. "
            "Brute-force execution policy: if blocked by cookie, sign-in, promo, feedback, or modal overlays, close or dismiss them. "
            "If the page errors, refresh once and retry the required action sequence. "
            "If navigation fails, return to the URL and continue until the objective is completed."
        ),
        called_from="assistant",
    )
    return True


def _looks_like_expedia_trip_request(normalized_prompt: str) -> bool:
    text = str(normalized_prompt or "").strip()
    if not text:
        return False

    travel_keywords = (
        "plan a trip",
        "plan trip",
        "book a trip",
        "travel",
        "vacation",
        "flight",
        "hotel",
        "itinerary",
    )
    has_travel_intent = any(keyword in text for keyword in travel_keywords)
    has_expedia = "expedia" in text
    return has_expedia or has_travel_intent


def _extract_trip_details(prompt: str):
    text = str(prompt or "").strip()
    lowered = text.lower()

    details = {
        "origin": "",
        "destination": "",
        "depart_date": "",
        "return_date": "",
        "adults": "1",
    }

    from_to_match = re.search(
        r"\bfrom\s+([a-zA-Z .'-]+?)\s+to\s+([a-zA-Z .'-]+?)(?:[,.]|\s|$)",
        text,
        flags=re.IGNORECASE,
    )
    if from_to_match:
        details["origin"] = from_to_match.group(1).strip()
        details["destination"] = from_to_match.group(2).strip()
    else:
        to_from_match = re.search(
            r"\bto\s+([a-zA-Z .'-]+?)\s+from\s+([a-zA-Z .'-]+?)(?:[,.]|\s|$)",
            text,
            flags=re.IGNORECASE,
        )
        if to_from_match:
            details["destination"] = to_from_match.group(1).strip()
            details["origin"] = to_from_match.group(2).strip()

    adults_match = re.search(
        r"\b(\d{1,2})\s+(adult|adults|traveler|travelers|people|persons)\b",
        lowered,
        flags=re.IGNORECASE,
    )
    if adults_match:
        details["adults"] = adults_match.group(1)

    depart_match = re.search(
        r"\b(?:depart(?:ing)?|leave|leaving|on)\s+([a-zA-Z]+\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",
        text,
        flags=re.IGNORECASE,
    )
    if depart_match:
        details["depart_date"] = _normalize_trip_date(depart_match.group(1))

    return_match = re.search(
        r"\b(?:return(?:ing)?|back\s+on)\s+([a-zA-Z]+\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",
        text,
        flags=re.IGNORECASE,
    )
    if return_match:
        details["return_date"] = _normalize_trip_date(return_match.group(1))

    return details


def _normalize_trip_date(raw_date: str) -> str:
    token = str(raw_date or "").strip()
    if not token:
        return ""

    now = datetime.now()
    date_formats = ["%B %d, %Y", "%b %d, %Y", "%B %d", "%b %d", "%m/%d/%Y", "%m/%d/%y", "%m/%d"]

    for fmt in date_formats:
        try:
            parsed = datetime.strptime(token, fmt)
            if "%Y" not in fmt and "%y" not in fmt:
                parsed = parsed.replace(year=now.year)
                if parsed.date() < now.date():
                    parsed = parsed.replace(year=now.year + 1)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return ""


def _resolve_chrome_executable() -> str:
    env_path = str(os.environ.get("ELI_CHROME_PATH", "")).strip()
    if env_path and os.path.exists(env_path):
        return env_path

    preferred_paths = (
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    )
    for path in preferred_paths:
        if os.path.exists(path):
            return path

    for candidate in ("chrome", "chrome.exe", "google-chrome", "google-chrome-stable"):
        resolved = shutil.which(candidate)
        if resolved and os.path.exists(resolved):
            return resolved
    return ""


def _open_expedia_in_chrome() -> bool:
    chrome_exe = _resolve_chrome_executable()
    if not chrome_exe:
        return False

    try:
        subprocess.Popen([chrome_exe, "--new-window"])  # Open browser first, then type URL into omnibox.
        time.sleep(1.2)
        chrome_hwnd, _ = find_window_by_title("google chrome")
        if chrome_hwnd:
            bring_to_foreground(chrome_hwnd)
        else:
            activate_windowt_title("google chrome")
        time.sleep(0.6)
        perform_simulated_keypress("Ctrl + L")
        pyautogui.write("expedia.com", interval=0.01)
        perform_simulated_keypress("Enter")
        time.sleep(1.1)

        # Self-heal: if we still don't see Expedia, open it directly in a fresh Chrome window.
        rows = open_windows_info()
        expedia_visible = any("expedia" in str(item[1]).lower() for item in rows)
        if not expedia_visible:
            subprocess.Popen([chrome_exe, "--new-window", "https://www.expedia.com"])
            time.sleep(1.0)

        # Make sure the browser is visibly foregrounded before returning.
        _ensure_browser_visible_for_expedia()
        return True
    except Exception as e:
        print(f"Chrome Expedia launch failed: {e}")
        return False


def _ensure_browser_visible_for_expedia() -> bool:
    """Force an Expedia/Chrome window to the foreground so actions run on a visible browser."""
    candidates = (
        "expedia",
        "google chrome",
        "chrome",
    )

    for attempt in range(6):
        # Aggressive fallback cadence for focus recovery when another app stole focus.
        if attempt in {2, 4}:
            try:
                perform_simulated_keypress("Win + D")
            except Exception as e:
                print(f"Browser visibility desktop reveal failed: {e}")
            time.sleep(0.12)

        if attempt >= 1:
            try:
                perform_simulated_keypress("Alt + Tab")
            except Exception as e:
                print(f"Browser visibility alt-tab failed: {e}")
            time.sleep(0.08)

        for title_hint in candidates:
            try:
                hwnd, resolved_title = find_window_by_title(title_hint)
            except Exception as e:
                print(f"Browser visibility lookup failed for '{title_hint}': {e}")
                hwnd, resolved_title = None, None

            if hwnd:
                try:
                    bring_to_foreground(hwnd)
                except Exception as e:
                    print(f"Browser visibility foreground failed: {e}")

                # Reinforce activation by title when available.
                try:
                    activate_windowt_title(resolved_title or title_hint)
                except Exception as e:
                    print(f"Browser visibility activate-by-title failed: {e}")

                # Keep browser fully visible and receive input focus deterministically.
                try:
                    perform_simulated_keypress("Win + Up")
                except Exception as e:
                    print(f"Browser visibility maximize failed: {e}")

                try:
                    perform_simulated_keypress("Ctrl + 1")
                except Exception as e:
                    print(f"Browser visibility first-tab focus failed: {e}")

                try:
                    size = pyautogui.size()
                    pyautogui.click(size.width // 2, 120)
                except Exception as e:
                    print(f"Browser visibility viewport click failed: {e}")

                time.sleep(0.15)
                return True

            try:
                activate_windowt_title(title_hint)
            except Exception:
                pass

        time.sleep(0.2)

    return False


def _dismiss_expedia_overlays_deterministic():
    """Run a fixed, deterministic sequence to dismiss common Expedia modal overlays."""
    # 1) First attempt: keyboard dismiss.
    for _ in range(2):
        try:
            perform_simulated_keypress("Escape")
        except Exception as e:
            print(f"Overlay killer Escape failed: {e}")
        time.sleep(0.2)

    # 2) Second attempt: deterministic text/button close heuristics.
    close_steps = [
        "click the X close button on the popup",
        "click close on the sign in popup",
        "click not now",
        "click no thanks",
        "click dismiss",
        "click continue without signing in",
    ]
    for step in close_steps:
        try:
            fast_act(single_step=step)
        except Exception as e:
            print(f"Overlay killer click heuristic failed for '{step}': {e}")
        time.sleep(0.2)

    # 3) Last deterministic fallback: click near top-right close icon region.
    try:
        size = pyautogui.size()
        fallback_x = max(50, size.width - 60)
        fallback_y = 170
        pyautogui.click(fallback_x, fallback_y)
    except Exception as e:
        print(f"Overlay killer coordinate fallback failed: {e}")


def _build_expedia_search_url(details) -> str:
    origin = str(details.get("origin", "")).strip()
    destination = str(details.get("destination", "")).strip()
    depart_date = str(details.get("depart_date", "")).strip()
    return_date = str(details.get("return_date", "")).strip()
    adults = str(details.get("adults", "1")).strip() or "1"

    if not origin or not destination or not depart_date:
        return "https://www.expedia.com/Flights"

    params = {
        "trip": "roundtrip" if return_date else "oneway",
        "leg1": f"from:{origin},to:{destination},departure:{depart_date}TANYT",
        "options": f"cabinclass:economy,adults:{adults},children:0,seniors:0,infantinlap:Y",
        "mode": "search",
    }
    if return_date:
        return_origin = destination
        return_destination = origin
        params["leg2"] = f"from:{return_origin},to:{return_destination},departure:{return_date}TANYT"

    query = urlencode(params, quote_via=quote_plus)
    return f"https://www.expedia.com/Flights-Search?{query}"


def _plan_trip_on_expedia(prompt: str) -> bool:
    details = _extract_trip_details(prompt)
    speaker("Opening Google Chrome and Expedia to plan your trip.")

    opened_in_chrome = _open_expedia_in_chrome()
    if not opened_in_chrome:
        # Fallback keeps trip flow working if Chrome is unavailable.
        activate_windowt_title("https://www.expedia.com")
        time.sleep(1.2)

    # Ensure Chrome/Expedia is visible before popup dismissal and planner handoff.
    _ensure_browser_visible_for_expedia()

    # Deterministic first-step overlay killer before planner handoff.
    _dismiss_expedia_overlays_deterministic()

    # Keep the browser in front in case dismissal shifted focus.
    _ensure_browser_visible_for_expedia()

    # Always hand over to the planner so execution continues end-to-end even when Expedia
    # shows transient errors, sign-in modals, or partially prefilled searches.
    assistant(
        assistant_goal=(
            "Use Google Chrome and Expedia.com to brute-force complete this flight booking end-to-end: "
            f"{prompt}. "
            f"Parsed trip details: origin={details.get('origin','') or 'unknown'}, "
            f"destination={details.get('destination','') or 'unknown'}, "
            f"depart={details.get('depart_date','') or 'unknown'}, "
            f"return={details.get('return_date','') or 'unknown'}, "
            f"adults={details.get('adults','1')}. "
            "If Chrome is not available, continue in whatever browser is active. "
            "First dismiss any sign-in overlays or promotional popups. "
            "Brute-force execution policy: do not stop at search results. Keep progressing through "
            "flight selection, fare selection, traveler details, and checkout screens. "
            "If Expedia shows an error like 'Sorry, we're having a problem on our end', click Retry. "
            "If Retry fails, rebuild the search form manually from the user request and run search again. "
            "If blocked by stale state, open a fresh tab to expedia.com and retry the flow. "
            "Success condition: reach the final booking review or payment confirmation step. "
            "Never submit unauthorized purchases and never bypass protected auth or payment controls. "
            "If mandatory booking/payment fields are missing, pause and ask only for missing user-provided fields, "
            "then resume automation from that exact step and continue to final review/confirmation."
        ),
        called_from="assistant",
    )
    return True


def _try_edge_actions(raw_action: str) -> bool:
    if str(os.environ.get("ELI_EDGE_ACTIONS_ENABLED", "")).strip().lower() not in {"1", "true", "yes", "on"}:
        return False

    normalized = raw_action.strip().lower()
    task_id = ""
    prefixed = (
        normalized.startswith("edge task ")
        or normalized.startswith("browser task ")
        or normalized.startswith("edge run ")
    )

    if prefixed:
        if " " in normalized:
            parts = raw_action.split(" ", 2)
            task_id = parts[2].strip() if len(parts) >= 3 else ""
        if not task_id:
            message_queue.put("Edge Actions enabled, but task id was missing.")
            return True
    else:
        try:
            from edge_actions.task_catalog import resolve_task_id_from_text
            task_id = resolve_task_id_from_text(raw_action) or ""
        except Exception:
            task_id = ""

        if not task_id:
            return False

    try:
        from edge_actions import EdgeActionRunner
        runner = EdgeActionRunner()
        result = runner.run_task(task_id=task_id, inputs={"objective": raw_action})
        message_queue.put(f"Edge task finished: {result.get('status')} ({result.get('trace_path')})")
    except Exception as e:
        message_queue.put(f"Edge task failed: {e}")
    return True


def _try_autoresearch_word_actions(raw_action: str) -> bool:
    normalized = str(raw_action or "").strip().lower()
    if not normalized:
        return False

    is_autoresearch_word_prompt = normalized.startswith("word research ") or normalized.startswith("winword research ")
    if not is_autoresearch_word_prompt:
        return False

    if str(os.environ.get("ENABLE_AUTORESEARCH_WORD", "false")).strip().lower() not in {"1", "true", "yes", "on"}:
        message_queue.put("Autoresearch Word integration is disabled. Set ENABLE_AUTORESEARCH_WORD=true")
        return True

    try:
        from edge_actions.autoresearch_word import AutoresearchWordBridge

        bridge = AutoresearchWordBridge()
        result = bridge.run_from_prompt(raw_action)
        status = str(result.get("status", "unknown"))
        detail = str(result.get("blocked_reason") or result.get("message") or "")
        if detail:
            message_queue.put(f"Autoresearch Word status: {status} ({detail})")
        else:
            message_queue.put(f"Autoresearch Word status: {status}")
    except Exception as e:
        message_queue.put(f"Autoresearch Word failed: {e}")
    return True


def _try_word_actions(raw_action: str) -> bool:
    normalized = str(raw_action or "").strip().lower()
    if not normalized:
        return False

    is_word_prompt = normalized.startswith("word ") or normalized.startswith("winword ")
    if not is_word_prompt:
        return False

    try:
        from edge_actions.word import WordWorkflowEngine, word_actions_enabled

        if not word_actions_enabled():
            message_queue.put("Word actions are disabled. Set ELI_WORD_ACTIONS_ENABLED=true")
            return True

        engine = WordWorkflowEngine()
        result = engine.run_prompt(raw_action)
        status = result.get("status", "unknown")
        message_queue.put(f"Word action status: {status}")
    except Exception as e:
        message_queue.put(f"Word action failed: {e}")
    return True


def start_drag(event):
    # Record the starting point for dragging
    global offset_x, offset_y, click_time
    offset_x = event.x
    offset_y = event.y
    click_time = time.time()


def show_message(event=None, message="Hello! How can I help you?"):
    # Function to show a pop-up message bubble
    message_window = Ctk.CTkToplevel(root)  # Create a new window
    message_window.overrideredirect(True)  # Remove the window border
    message_window.attributes('-topmost', True)  # Keep the window on top
    # Get dimensions for the message window
    # temp_label = Ctk.CTkLabel(message_window, text=message)
    # temp_label.pack()
    message_window.update_idletasks()  # Update the layout to get size
    message_width = message_window.winfo_width()
    message_height = message_window.winfo_height()
    # temp_label.destroy()
    if event:
        pos_x = event.x_root + 20
        pos_y = event.y_root - message_height // 2
    else:
        # Calculate position based on assistant current position
        pos_x = root.winfo_x() + label.winfo_width() + 10
        pos_y = root.winfo_y() + label.winfo_height() // 2 - message_height // 2
    # Adjust position if the message window goes offscreen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    if pos_x + message_width > screen_width:
        pos_x = screen_width - message_width
    if pos_y + message_height > screen_height:
        pos_y = screen_height - message_height
    if pos_y < 0:
        pos_y = 0
    # Set the geometry and display the message
    message_window.geometry(f'+{pos_x}+{pos_y}')
    message_label = Ctk.CTkLabel(message_window, text=message)
    message_label.configure(corner_radius=6, fg_color="#e1f2f1", text_color="black", bg_color="gray")
    message_label.pack(padx=0, pady=0)
    # Close the message bubble after a dynamic duration based on words count, minimum 3 seconds
    timeout = max(3000, calculate_duration_of_speech(message))
    message_window.after(timeout, message_window.destroy)

def create_context_menu(event_x_root, event_y_root):
    global context_menu_ref, assistant_voice_enabled, assistant_anim_enabled, assistant_subtitles_enabled, assistant_voice_recognition_enabled  # Use the global references

    # Create a custom context menu using Ctk widgets
    context_menu = Ctk.CTkToplevel(root)
    context_menu.overrideredirect(True)
    context_menu.attributes('-topmost', True)
    context_menu.attributes('-alpha', 0.95)  # Set transparency (0.0 to 1.0)
    # Set the theme to light
    # Change buttons color
    # Ctk.set_default_color_theme("dark-blue")  # Themes: blue (default), dark-blue, green
    # context_menu visual options
    context_menu.configure(borderless=True, border_color="black")
    context_menu.bind("<Escape>", lambda e: context_menu.destroy())
    context_menu.bind("<FocusOut>", lambda e: context_menu.destroy())
    # Frame to hold menu items
    menu_frame = Ctk.CTkFrame(context_menu)
    menu_frame.pack()
    # Wrapper function to execute command and close the menu
    def menu_command(command):
        if callable(command):
            print(f"Executing command: {command}")
            command()  # Execute command if it's callable
        else:
            print(f"Command '{command}' not implemented yet")
        context_menu.destroy()  # Destroy the menu after executing the command

    # Buttons with commands
    Ctk.CTkButton(menu_frame, text="Call assistant", command=lambda: menu_command(generate_assistant_test_case(False))).pack(fill="x")
    Ctk.CTkButton(menu_frame, text="Fast action", command=lambda: menu_command(generate_assistant_test_case(True))).pack(fill="x")
    Ctk.CTkButton(menu_frame, text="Content analysis", command=lambda: menu_command(dummy_command)).pack(fill="x")

    # Add separator or space between groups of options (This is an improvisation since Ctk doesn't have a separator widget)
    Ctk.CTkLabel(menu_frame, text="", height=3).pack(fill="x")

    # Toggle buttons for voice, animation, and subtitles with the current status check
    volume_option = "Enable assistant voice" if not assistant_voice_enabled else "Disable assistant voice"
    anim_option = "Enable animations" if not assistant_anim_enabled else "Disable animations"
    subs_option = "Enable subtitles" if not assistant_subtitles_enabled else "Disable subtitles"
    voice_option = "Enable voice recognition" if not assistant_voice_recognition_enabled else "Disable voice recognition"
    # Add the buttons to the menu frame
    Ctk.CTkButton(menu_frame, text=volume_option, command=lambda: menu_command(toggle_volume)).pack(fill="x")
    Ctk.CTkButton(menu_frame, text=anim_option, command=lambda: menu_command(toggle_animations)).pack(fill="x")
    Ctk.CTkButton(menu_frame, text=subs_option, command=lambda: menu_command(toggle_subtitles)).pack(fill="x")
    Ctk.CTkButton(menu_frame, text=voice_option, command=lambda: menu_command(toggle_voice_recognition)).pack(fill="x")
    # Add separator or space between groups of options (This is an improvisation since Ctk doesn't have a separator widget)
    Ctk.CTkLabel(menu_frame, text="", height=3).pack(fill="x")
    # Extra options
    Ctk.CTkButton(menu_frame, text="Minimize", command=lambda: menu_command(minimize_assistant)).pack(fill="x")
    Ctk.CTkButton(menu_frame, text="Hide", command=lambda: menu_command(root.withdraw)).pack(fill="x")
    Ctk.CTkButton(menu_frame, text="Reset", command=lambda: menu_command(restart_assistant)).pack(fill="x")
    Ctk.CTkButton(menu_frame, text="Stop", command=lambda: menu_command(stop_assistant)).pack(fill="x")
    Ctk.CTkLabel(menu_frame, text="", height=3).pack(fill="x")
    Ctk.CTkButton(menu_frame, text="Back...", command=lambda: menu_command(root.deiconify)).pack(fill="x")

    # Update the layout to calculate the width and height
    context_menu.update_idletasks()
    menu_width = menu_frame.winfo_reqwidth()
    menu_height = menu_frame.winfo_reqheight()

    # Position the menu at the cursor position
    # If the menu goes off the screen to the right, move it left; same for bottom
    if event_x_root + menu_width > root.winfo_screenwidth():
        event_x_root = root.winfo_screenwidth() - menu_width - 93
    if event_y_root + menu_height > root.winfo_screenheight():
        event_y_root = root.winfo_screenheight() - menu_height - 100

    context_menu.geometry(f"{menu_width}x{menu_height}+{event_x_root}+{event_y_root}")
    context_menu.focus_force()  # Force focus on the menu
    context_menu_ref = context_menu  # Store the reference to the menu in a global variable
    return context_menu_ref

def minimize_assistant():
    root.withdraw()
    root.overrideredirect(False)
    root.iconify()
    # root.overrideredirect(True)


def show_config(event):
    # Function to display the settings menu using a custom context menu
    create_context_menu(event.x_root, event.y_root)

# Just for example purpose, you will replace this with actual commands
def dummy_command():
    speaker("Dummy item clicked")
    print("Dummy item clicked")

def generate_assistant_test_case(fast_act=False):
    # Function to perform a fast action
    if fast_act:
        speaker("What's the fast action step?")
        print("What's the fast action step?")
        create_input_bubble(fast_act)
    else:
        speaker("What's the test-case to generate?")
        print("What's the test-case to generate?")
        create_input_bubble(fast_act)

def toggle_voice_recognition():
    global assistant_voice_recognition_enabled
    assistant_voice_recognition_enabled = not assistant_voice_recognition_enabled
    if assistant_voice_recognition_enabled:
        show_message(None, "Voice recognition enabled")
        speaker("Voice recognition enabled")
    else:
        show_message(None, "Voice recognition disabled")
        speaker("Voice recognition disabled")


def toggle_animations():
    global assistant_anim_enabled
    assistant_anim_enabled = not assistant_anim_enabled
    if assistant_anim_enabled:
        animate_blink()  # Restart blinking animation
        animate_move()   # Restart moving animation
        show_message(None, "Animations enabled")
    else:
        show_message(None, "Animations disabled")


def toggle_subtitles():
    global assistant_subtitles_enabled
    assistant_subtitles_enabled = not assistant_subtitles_enabled
    if assistant_subtitles_enabled:
        show_message(None, "Subtitles enabled")
        set_subtitles(True)
    else:
        set_subtitles(False)
        show_message(None, "Subtitles disabled")


def toggle_volume():
    global assistant_voice_enabled
    assistant_voice_enabled = not assistant_voice_enabled
    if assistant_voice_enabled:
        show_message(None, "Assistant voice enabled")
        set_volume(0.25)
        speaker("Voice enabled")
    else:
        show_message(None, "Assistant voice disabled")
        set_volume(0)


def stop_assistant():
    root.destroy()
    pass


def restart_assistant():
    _clear_chat_history()
    root.destroy()
    create_app()
    pass


def calculate_duration_of_speech(text, lang='en', wpm=150):
    # Estimate the duration the subtitles should be displayed based on words per minute (WPM)
    duration_in_seconds = (len(text.split()) / wpm) * 60
    return int(duration_in_seconds * 1000)  # Convert to milliseconds for tkinter's after method


def animate_blink():
    # Function for blinking animation
    label.configure(image=assistant_blink_photo)
    root.after(150, lambda: label.configure(image=assistant_photo))
    next_blink = random.randint(500, 10000) if assistant_anim_enabled else 10000
    root.after(next_blink, animate_blink)


def animate_move(step=0, direction=1, amplitude=3, start_time=1):
    global position_bottom, is_dragging
    max_steps = 15
    if start_time is None:
        start_time = time.time()
    if assistant_anim_enabled and not is_dragging:
        new_position = position_bottom + amplitude * direction * (1 - abs(step / max_steps * 2 - 1))
        root.geometry(f'+{position_right}+{int(new_position)}')
        next_step = step + 1
        if next_step > max_steps:
            current_time = time.time()
            next_step = 0
            movement_duration = current_time - start_time
            if 1 <= movement_duration <= 2:
                direction = -direction
                start_time = current_time
            amplitude = random.randint(0, 3)
        random_delay = random.randint(30, 200)
        root.after(random_delay, lambda: animate_move(next_step, direction, amplitude, start_time))


def listen_thread():
    global assistant_voice_recognition_enabled
    print("Assistant listening thread started...")
    while True:
        if not assistant_voice_recognition_enabled:
            # If voice recognition got disabled, wait for a bit before checking again ToDo: Maybe use a condition variable instead, but im planning on performing other actions here. Like a low power mode or something like that works for now
            time.sleep(1)
            # print("Voice recognition disabled, waiting...")
            continue

        with sr.Microphone() as source:
            print("Listening...")
            try:
                audio = recognizer.listen(source, timeout=1.5)
                if assistant_voice_recognition_enabled:
                    message = recognizer.recognize_google(audio)
                    message_low = message.lower()
                    # Speaking the message
                    message_queue.put(message)
                    # Only process the audio if voice recognition is enabled
                    if "okay computer" in message_low[0:13] or assistant_name_handle.lower() in message_low[0:11]:
                        message_queue.put("Assistant here! How can I help you?")
                        ok_computer = listen_to_speech()
                        if ok_computer:
                            show_message(None, ok_computer)
                            auto_prompt(ok_computer)
                    elif "open" in message_low[0:4]:
                        if len(message) < 18:
                            print("Opening the program: ", message)
                            activate_windowt_title(message.strip("open "))
                        else:
                            assistant(message)
                    elif "stop" in message_low:
                        print("Stopping...")
                        stop_assistant()
                    elif "double click" in message_low[0:12]:
                        print("Double clicking on:", message)
                        fast_act(single_step=message.strip("double "), double_click=True)
                    # Or if message starts with the first word click and
                    elif "click on" in message_low[0:8] or "click the" in message_low[0:9] or "click" in message_low[0:5]:
                        print("Clicking on:", message)
                        fast_act(single_step=message)
                    elif "press" in message_low[0:5]:
                        print("press: ", message)
                        perform_simulated_keypress(message.strip("press ").strip(""))
                    elif "type" in message_low[0:4] or "write" in message_low[0:5] or "bright" in message_low[0:6] or "great" in message_low[0:5]:
                        # Remove "bright ", "write ", "type ", "great " from the message:
                        new_message = message.replace("bright ", "").replace("write ", "").replace("type ", "").replace("great ", "")
                        print("Typing:", new_message)
                        write_action(goal=new_message, last_step="text_entry")
                    elif "reminder" in message_low or "remind" in message_low or "timer" in message_low or "alarm" in message_low:
                        # Call internal_clock.py - Generated.
                        # Here's thoughts of when remind the user if is not noticing any important upcoming event:
                        # Advice the user for upcoming events. Add reminders, timers, alarms, etc.
                        print("Reminder: ", message)
                    elif "scroll" in message_low[0:6]:
                        print("Scrolling: ", message)
                        import pyautogui
                        pyautogui.scroll(-850)
                    else:
                        auto_prompt(message)
                else:
                    # Voice recognition was disabled while audio was being processed, skip it
                    continue
            except (sr.UnknownValueError, sr.RequestError, sr.WaitTimeoutError):
                # If you want to handle specific errors, you can separate them with additional except blocks
                pass


def _voice_thread_enabled() -> bool:
    return str(os.environ.get("ELI_DISABLE_VOICE_THREAD", "")).strip().lower() not in {"1", "true", "yes", "on"}


# Start the listening thread during normal runtime, but allow tests/importers to opt out.
listening_thread = None
if _voice_thread_enabled():
    listening_thread = threading.Thread(target=listen_thread, daemon=True)
    listening_thread.start()


def auto_prompt(message):
    # Voice/input autoprompt should prioritize Expedia/travel automation before chat routing.
    if _looks_like_expedia_trip_request(str(message or "").lower()):
        run_fast_action(message)
        return

    if _prefer_conversation(message, action_mode=False):
        response = generate_conversational_response(message)
        message_queue.put(response)
        return

    role_function = auto_role(message)
    print(f"Assistant Role Selection: {role_function}")
    if "windows_assistant" in role_function:
        msg = role_function.replace('windows_assistant', '').strip(' - ')
        message_queue.put(msg)
        # Start the assistant in a new thread:
        assistant_thread = threading.Thread(target=run_assistant, args=(message,))
        assistant_thread.start()
    elif "joyful_conversation" in role_function:
        response = generate_conversational_response(message)
        message_queue.put(response)
    else:
        # Fallback to Conversational AI if classification is ambiguous
        response = generate_conversational_response(message)
        message_queue.put(response)


def load_image(file_path, scale=0.125):
    # Helper function to load and scale the image
    image = Image.open(file_path)
    original_width, original_height = image.size
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    image = image.resize((new_width, new_height), Image.Resampling.BICUBIC)
    ctk_image = Ctk.CTkImage(light_image=image, size=(new_width, new_height))
    return ctk_image, new_width, new_height


def create_app():
    global root, label, assistant_photo, assistant_dragging_photo, assistant_blink_photo, assistant_anim_enabled, is_dragging, position_right, position_bottom, drag_time, \
        assistant_voice_enabled, assistant_subtitles_enabled, assistant_name_handle, assistant_photo_width, assistant_photo_height, scale_factor # Add width and height globals
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = Ctk.CTk()
    root.title("AI Agent")
    root.iconbitmap("media/headico.ico")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.wm_attributes("-transparentcolor", 'gray')

    # Load images and get their sizes
    assistant_photo, assistant_photo_width, assistant_photo_height = load_image("media/assistant_transparent.png")
    assistant_dragging_photo, _, _ = load_image("media/assistant_transparent_dragging.png")
    assistant_blink_photo, _, _ = load_image("media/assistant_transparent_blink.png")
    label = Ctk.CTkLabel(root, image=assistant_photo, bg_color="gray", cursor="hand2", text="")
    label.pack()
    label.bind('<ButtonPress-1>', start_drag)
    label.bind('<B1-Motion>', on_drag)
    label.bind('<ButtonRelease-1>', end_drag)
    label.bind('<ButtonPress-3>', show_config)

    # Calculate initial position (bottom right)
    user32 = ctypes.windll.user32
    work_area = ctypes.wintypes.RECT()
    user32.SystemParametersInfoW(48, 0, ctypes.byref(work_area), 0)
    screen_width = work_area.right - work_area.left
    screen_height = work_area.bottom - work_area.top
    # Keep the icon above the taskbar and a bit left from the edge.
    position_right = int(screen_width - assistant_photo_width - 180)
    position_bottom = int(screen_height - assistant_photo_height - 12)
    drag_time = time.time()

    # Set initial geometry to place the assistant at the bottom right
    root.geometry(f'+{position_right}+{position_bottom}')
    is_dragging = False  # Flag to track dragging state
    root.after(1000, animate_blink)  # Start the blinking animation
    root.after(1000, animate_move)  # Start the moving animation
    root.after(100, process_queue)  # Start processing the message queue
    # Call the mainloop
    root.mainloop()
    pass

if __name__ == "__main__":
    create_app()