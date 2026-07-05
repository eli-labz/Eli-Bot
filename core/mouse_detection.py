import ctypes
import os
from pathlib import Path
import win32api
import win32con
from env_loader import load_env


THIRD_PARTY_DIR = Path(__file__).resolve().parent / "third_party"
MOUSEMUX_SDK_DIR = THIRD_PARTY_DIR / "Mousemux--WinSDK"


load_env()


def _is_truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _mousemux_runtime_path():
    configured = os.environ.get("ELI_MOUSEMUX_RUNTIME", "").strip()
    if configured:
        return Path(configured)

    for candidate in ("mousemux_sdk.exe", "main.exe", "mousemux.dll"):
        path = MOUSEMUX_SDK_DIR / candidate
        if path.exists():
            return path
    return None


def _get_cursor_shape_from_mousemux():
    if not _is_truthy(os.environ.get("MOUSEMUX_ENABLE", "0")):
        return None

    agent_uid = os.environ.get("MOUSEMUX_AGENT_UID", "").strip()
    if agent_uid and "ELI_MOUSEMUX_AGENT_UID" not in os.environ:
        os.environ["ELI_MOUSEMUX_AGENT_UID"] = agent_uid

    runtime = _mousemux_runtime_path()
    if runtime is None:
        return None
    # MouseMux SDK integration is optional. If runtime is present but no Python bridge is
    # configured yet, fall back to native Windows cursor shape detection.
    return None

# Define the CURSORINFO structure
class CURSORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_int),
                ("flags", ctypes.c_int),
                ("hCursor", ctypes.c_void_p),
                ("ptScreenPos", ctypes.c_long * 2)]

def get_cursor_shape():
    sdk_cursor_shape = _get_cursor_shape_from_mousemux()
    if sdk_cursor_shape:
        return sdk_cursor_shape

    cursor_info = CURSORINFO()
    cursor_info.cbSize = ctypes.sizeof(CURSORINFO)
    ctypes.windll.user32.GetCursorInfo(ctypes.byref(cursor_info))

    # Load the standard cursors to compare
    cursor_arrow = win32api.LoadCursor(0, win32con.IDC_ARROW)
    cursor_ibeam = win32api.LoadCursor(0, win32con.IDC_IBEAM)
    cursor_hand = win32api.LoadCursor(0, win32con.IDC_HAND)
    cursor_wait = win32api.LoadCursor(0, win32con.IDC_WAIT)
    cursor_cross = win32api.LoadCursor(0, win32con.IDC_CROSS)

    # Compare the current cursor with the standard cursors
    if cursor_info.hCursor == cursor_arrow:
        return "Arrow"
    elif cursor_info.hCursor == cursor_ibeam:
        return "The cursor is active for Text Input (I-beam)"
    elif cursor_info.hCursor == cursor_hand:
        return "The cursor is 'Hand' (A link is select)"
    elif cursor_info.hCursor == cursor_wait:
        return "The cursor is 'Wait' (Busy) - Hourglass or Watch"
    elif cursor_info.hCursor == cursor_cross:
        return "The cursor is 'Cross'"
    else:
        return "Other"

# while True:
#     cursor_shape = get_cursor_shape()
#     print(f"Cursor shape: {cursor_shape}")
#     time.sleep(1)
