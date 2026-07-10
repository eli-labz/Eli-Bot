import os
from queue import Queue
import json
import sys
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

# Prevent microphone thread side effects while importing assistant module in tests.
os.environ["ELI_DISABLE_VOICE_THREAD"] = "1"

ROOT_DIR = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT_DIR / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import assistant  # noqa: E402


class SlashCommandsTests(unittest.TestCase):
    def setUp(self):
        self.original_queue = assistant.message_queue
        self.original_chat = assistant.generate_conversational_response
        self.original_action = assistant.run_fast_action
        self.original_assistant = assistant.run_assistant
        self.original_tempest = assistant.run_tempest_action
        self.original_clear = assistant._clear_chat_history

        self.queue = Queue()
        assistant.message_queue = self.queue

        self.last_action = None
        self.last_assistant = None
        self.last_tempest = None
        self.cleared = False

        def fake_chat(text):
            return f"chat:{text}"

        def fake_action(text):
            self.last_action = text

        def fake_assistant(text):
            self.last_assistant = text

        def fake_tempest(text):
            self.last_tempest = text

        def fake_clear():
            self.cleared = True

        assistant.generate_conversational_response = fake_chat
        assistant.run_fast_action = fake_action
        assistant.run_assistant = fake_assistant
        assistant.run_tempest_action = fake_tempest
        assistant._clear_chat_history = fake_clear

    def tearDown(self):
        assistant.message_queue = self.original_queue
        assistant.generate_conversational_response = self.original_chat
        assistant.run_fast_action = self.original_action
        assistant.run_assistant = self.original_assistant
        assistant.run_tempest_action = self.original_tempest
        assistant._clear_chat_history = self.original_clear

    def test_help_command(self):
        handled = assistant._handle_slash_command("/help")
        self.assertTrue(handled)
        self.assertIn("Slash commands:", self.queue.get_nowait())

    def test_chat_command(self):
        handled = assistant._handle_slash_command("/chat hello")
        self.assertTrue(handled)
        self.assertEqual("chat:hello", self.queue.get_nowait())

    def test_action_command(self):
        handled = assistant._handle_slash_command("/action open notepad")
        self.assertTrue(handled)
        self.assertEqual("open notepad", self.last_action)

    def test_assistant_command(self):
        handled = assistant._handle_slash_command("/assistant write a summary")
        self.assertTrue(handled)
        self.assertEqual("write a summary", self.last_assistant)

    def test_word_command_prefixes_instruction(self):
        handled = assistant._handle_slash_command("/word open")
        self.assertTrue(handled)
        self.assertEqual("word open", self.last_action)

    def test_clear_command(self):
        handled = assistant._handle_slash_command("/clear")
        self.assertTrue(handled)
        self.assertTrue(self.cleared)
        self.assertIn("Conversation memory cleared.", self.queue.get_nowait())

    def test_tempest_command(self):
        handled = assistant._handle_slash_command("/tempest test authorized objective")
        self.assertTrue(handled)
        self.assertEqual("test authorized objective", self.last_tempest)

    def test_computer_use_command(self):
        handled = assistant._handle_slash_command("/computer open calculator")
        self.assertTrue(handled)
        self.assertEqual("open calculator", self.last_action)

    def test_unknown_command(self):
        handled = assistant._handle_slash_command("/notreal")
        self.assertTrue(handled)
        self.assertIn("Unknown slash command", self.queue.get_nowait())

    def test_brain_status_command(self):
        handled = assistant._handle_slash_command("/brain-status")
        self.assertTrue(handled)
        self.assertIn("Brain status", self.queue.get_nowait())

    def test_brain_status_profile_tuning(self):
        with patch.dict("assistant.os.environ", {}, clear=False):
            handled = assistant._handle_slash_command("/brain-status profile cautious")
            self.assertTrue(handled)
            msg_1 = self.queue.get_nowait()
            msg_2 = self.queue.get_nowait()
            self.assertIn("profile updated", msg_1.lower())
            self.assertIn("brain status", msg_2.lower())

    def test_brain_status_levels_command(self):
        handled = assistant._handle_slash_command("/brain-status levels")
        self.assertTrue(handled)
        self.assertIn("Consciousness levels", self.queue.get_nowait())

    def test_brain_status_preset_command(self):
        with patch.dict("assistant.os.environ", {}, clear=False):
            handled = assistant._handle_slash_command("/brain-status preset aggressive")
            self.assertTrue(handled)
            msg_1 = self.queue.get_nowait()
            msg_2 = self.queue.get_nowait()
            self.assertIn("preset applied", msg_1.lower())
            self.assertIn("brain status", msg_2.lower())

    def test_brain_status_trend_command(self):
        handled = assistant._handle_slash_command("/brain-status trend chat")
        self.assertTrue(handled)
        self.assertIn("Brain trend", self.queue.get_nowait())

    def test_brain_status_mistakes_command(self):
        trace_dir = ROOT_DIR / "_tmp_test_traces_mistakes"
        trace_dir.mkdir(exist_ok=True)
        trace_file = trace_dir / "task_1.json"
        trace_payload = {
            "task_id": "task-1",
            "events": [
                {
                    "type": "consequence_assessment",
                    "unintended": True,
                    "severity": "high",
                    "summary": "Cross-host navigation after click",
                    "step": 1,
                    "timestamp": "2026-07-09T12:00:00+00:00",
                    "recommended_recovery": "revert_to_before_url",
                }
            ],
        }
        trace_file.write_text(json.dumps(trace_payload), encoding="utf-8")

        try:
            with patch.dict("assistant.os.environ", {"ELI_EDGE_ACTIONS_TRACE_DIR": str(trace_dir)}, clear=False):
                handled = assistant._handle_slash_command("/brain-status mistakes")
                self.assertTrue(handled)
                response = self.queue.get_nowait()
                self.assertIn("Brain mistakes summary", response)
                self.assertIn("Severity buckets:", response)
                self.assertIn("high=1", response)
                self.assertIn("Cross-host navigation after click", response)
        finally:
            try:
                trace_file.unlink(missing_ok=True)
            finally:
                trace_dir.rmdir()

    def test_brain_status_mistakes_with_limit(self):
        trace_dir = ROOT_DIR / "_tmp_test_traces_mistakes_limit"
        trace_dir.mkdir(exist_ok=True)
        trace_file = trace_dir / "task_2.json"
        trace_payload = {
            "task_id": "task-2",
            "events": [
                {
                    "type": "consequence_assessment",
                    "unintended": True,
                    "severity": "medium",
                    "summary": "Verification failed after action",
                    "step": 2,
                    "timestamp": "2026-07-09T12:01:00+00:00",
                    "recommended_recovery": "planner_recovery",
                }
            ],
        }
        trace_file.write_text(json.dumps(trace_payload), encoding="utf-8")

        try:
            with patch.dict("assistant.os.environ", {"ELI_EDGE_ACTIONS_TRACE_DIR": str(trace_dir)}, clear=False):
                handled = assistant._handle_slash_command("/brain-status mistakes 1")
                self.assertTrue(handled)
                response = self.queue.get_nowait()
                self.assertIn("last 1 unintended events", response)
                self.assertIn("Severity buckets:", response)
                self.assertIn("medium=1", response)
        finally:
            try:
                trace_file.unlink(missing_ok=True)
            finally:
                trace_dir.rmdir()

    def test_tempest_strict_command_toggles_state(self):
        with patch.dict("assistant.os.environ", {}, clear=False):
            handled_on = assistant._handle_slash_command("/tempest-strict on")
            self.assertTrue(handled_on)
            self.assertEqual("1", assistant.os.environ.get("ELI_TEMPEST_STRICT_MODE"))

            handled_status = assistant._handle_slash_command("/tempest-strict status")
            self.assertTrue(handled_status)
            msg_on = self.queue.get_nowait()
            msg_status = self.queue.get_nowait()
            self.assertIn("enabled", msg_on.lower())
            self.assertIn("tempest strict mode", msg_status.lower())

            handled_off = assistant._handle_slash_command("/tempest-strict off")
            self.assertTrue(handled_off)
            self.assertEqual("0", assistant.os.environ.get("ELI_TEMPEST_STRICT_MODE"))


class ForcedComputerUsePhraseTests(unittest.TestCase):
    def test_extract_forced_goal(self):
        goal = assistant._extract_forced_computer_use_goal("BRUTE FORCE the agent for Computer Use open notepad")
        self.assertEqual("open notepad", goal)

    def test_extract_forced_goal_no_trigger(self):
        goal = assistant._extract_forced_computer_use_goal("how are you today")
        self.assertEqual("", goal)


class ExpediaIntentDetectionTests(unittest.TestCase):
    def test_book_me_flight_is_detected_as_trip_intent(self):
        text = "Book me a flight to Washington D.C on July 28, 2026."
        self.assertTrue(assistant._looks_like_expedia_trip_request(text.lower()))


class ExpediaChromeWorkflowTests(unittest.TestCase):
    def test_open_expedia_in_chrome_types_url(self):
        with patch("assistant._resolve_chrome_executable", return_value=r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"), patch(
            "assistant.subprocess.Popen"
        ) as mock_popen, patch("assistant.find_window_by_title", return_value=(12345, "Some Tab - Google Chrome")), patch(
            "assistant.bring_to_foreground"
        ) as mock_foreground, patch("assistant.activate_windowt_title") as mock_activate, patch(
            "assistant.perform_simulated_keypress"
        ) as mock_press, patch("assistant.pyautogui.write") as mock_write, patch(
            "assistant.open_windows_info", return_value=[(1, "Expedia Travel: Vacation Homes, Hotels, Car Rentals, Flights & More")]
        ), patch("assistant.time.sleep"):
            opened = assistant._open_expedia_in_chrome()
            self.assertTrue(opened)
            mock_popen.assert_called_once()
            self.assertTrue(mock_foreground.called)
            self.assertTrue(mock_activate.called)
            mock_press.assert_any_call("Ctrl + L")
            mock_press.assert_any_call("Enter")
            mock_write.assert_called_once()

    def test_plan_trip_on_expedia_falls_back_when_chrome_missing(self):
        with patch("assistant._open_expedia_in_chrome", return_value=False), patch("assistant.activate_windowt_title") as mock_activate, patch(
            "assistant.assistant"
        ) as mock_assistant, patch("assistant._dismiss_expedia_overlays_deterministic") as mock_dismiss, patch(
            "assistant._ensure_browser_visible_for_expedia"
        ) as mock_visible, patch("assistant.speaker"), patch("assistant.time.sleep"):
            handled = assistant._plan_trip_on_expedia("book a trip from Miami to Seattle departing July 15 for 2 adults")
            self.assertTrue(handled)
            mock_activate.assert_called_with("https://www.expedia.com")
            mock_dismiss.assert_called_once()
            self.assertGreaterEqual(mock_visible.call_count, 2)
            self.assertTrue(mock_assistant.called)
            goal_text = mock_assistant.call_args.kwargs.get("assistant_goal", "")
            self.assertIn("brute-force complete this flight booking end-to-end", goal_text.lower())
            self.assertIn("success condition: reach the final booking review or payment confirmation step", goal_text.lower())
            self.assertIn("never submit unauthorized purchases", goal_text.lower())
            self.assertIn("pause and ask only for missing user-provided fields", goal_text.lower())

    def test_ensure_browser_visible_for_expedia_foregrounds_window(self):
        with patch("assistant.find_window_by_title", return_value=(333, "Expedia - Google Chrome")), patch(
            "assistant.bring_to_foreground"
        ) as mock_foreground, patch("assistant.activate_windowt_title") as mock_activate, patch("assistant.time.sleep"):
            visible = assistant._ensure_browser_visible_for_expedia()
            self.assertTrue(visible)
            mock_foreground.assert_called_once_with(333)
            self.assertTrue(mock_activate.called)

    def test_ensure_browser_visible_for_expedia_uses_aggressive_fallback_when_no_window(self):
        with patch("assistant.find_window_by_title", return_value=(None, None)), patch(
            "assistant.activate_windowt_title", side_effect=Exception("no title match")
        ), patch("assistant.perform_simulated_keypress") as mock_keys, patch(
            "assistant.pyautogui.size", return_value=SimpleNamespace(width=1200, height=800)
        ), patch("assistant.pyautogui.click") as mock_click, patch("assistant.time.sleep"):
            visible = assistant._ensure_browser_visible_for_expedia()
            self.assertFalse(visible)
            self.assertGreaterEqual(mock_keys.call_count, 2)
            mock_click.assert_not_called()


class TempestFirstExecutionTests(unittest.TestCase):
    def test_run_bruteforce_action_uses_tempest_first_and_stops_on_success(self):
        with patch("assistant.run_tempest_action", return_value=True) as mock_tempest, patch(
            "assistant._try_autoresearch_word_actions"
        ) as mock_autoresearch:
            assistant._run_bruteforce_action("click search")
            mock_tempest.assert_called_once_with("click search")
            mock_autoresearch.assert_not_called()

    def test_run_bruteforce_action_falls_back_when_tempest_fails(self):
        with patch("assistant.run_tempest_action", return_value=False) as mock_tempest, patch(
            "assistant._try_autoresearch_word_actions", return_value=False
        ), patch("assistant._try_word_actions", return_value=False), patch("assistant._try_edge_actions", return_value=False), patch(
            "assistant._extract_bash_command", return_value=""
        ), patch("assistant._try_launch_exe_from_prompt", return_value=False), patch(
            "assistant._looks_like_expedia_trip_request", return_value=False
        ), patch("assistant._extract_any_url_from_text", return_value=""), patch(
            "assistant.get_word_workflow_steps", return_value=[]
        ), patch("assistant.fast_act", return_value=True) as mock_fast_act:
            assistant._run_bruteforce_action("click search")
            mock_tempest.assert_called_once_with("click search")
            self.assertGreaterEqual(mock_fast_act.call_count, 1)

    def test_run_bruteforce_action_strict_mode_blocks_local_fallback_on_tempest_failure(self):
        with patch.dict("assistant.os.environ", {"ELI_TEMPEST_STRICT_MODE": "1"}, clear=False), patch(
            "assistant.run_tempest_action", return_value=False
        ) as mock_tempest, patch("assistant._try_autoresearch_word_actions") as mock_autoresearch:
            assistant._run_bruteforce_action("click search")
            mock_tempest.assert_called_once_with("click search")
            mock_autoresearch.assert_not_called()

    def test_overlay_killer_runs_escape_click_and_coordinate_fallback(self):
        with patch("assistant.perform_simulated_keypress") as mock_keys, patch("assistant.fast_act") as mock_fast_act, patch(
            "assistant.pyautogui.size", return_value=SimpleNamespace(width=1200, height=800)
        ), patch("assistant.pyautogui.click") as mock_click, patch("assistant.time.sleep"):
            assistant._dismiss_expedia_overlays_deterministic()
            self.assertGreaterEqual(mock_keys.call_count, 2)
            self.assertGreaterEqual(mock_fast_act.call_count, 1)
            mock_click.assert_called_once()


class ExecutableLaunchPromptTests(unittest.TestCase):
    def setUp(self):
        self.original_queue = assistant.message_queue
        self.queue = Queue()
        assistant.message_queue = self.queue

    def tearDown(self):
        assistant.message_queue = self.original_queue

    def test_open_exe_from_prompt_uses_path_resolution(self):
        exe_path = r"C:\Windows\System32\notepad.exe"
        with patch("assistant.shutil.which", side_effect=lambda name: exe_path if "notepad" in str(name).lower() else None), patch(
            "assistant.subprocess.Popen"
        ) as mock_popen:
            handled = assistant._try_launch_exe_from_prompt("open notepad.exe")
            self.assertTrue(handled)
            mock_popen.assert_called_once()
            self.assertIn("Launched EXE", self.queue.get_nowait())

    def test_launch_without_extension_adds_exe(self):
        exe_path = r"C:\Windows\System32\calc.exe"
        with patch("assistant.shutil.which", side_effect=lambda name: exe_path if str(name).lower() == "calc.exe" else None), patch(
            "assistant.subprocess.Popen"
        ) as mock_popen:
            handled = assistant._try_launch_exe_from_prompt("launch calc")
            self.assertTrue(handled)
            mock_popen.assert_called_once()
            self.assertIn("Launched EXE", self.queue.get_nowait())

    def test_non_exe_prompt_is_not_handled(self):
        handled = assistant._try_launch_exe_from_prompt("hello friend")
        self.assertFalse(handled)

    def test_exe_prompt_reports_not_found(self):
        with patch("assistant.shutil.which", return_value=None):
            handled = assistant._try_launch_exe_from_prompt("open missingtool.exe")
            self.assertTrue(handled)
            self.assertIn("Executable not found", self.queue.get_nowait())


if __name__ == "__main__":
    unittest.main()
