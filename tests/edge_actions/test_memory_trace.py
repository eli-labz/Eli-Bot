import json
import tempfile
import unittest
from pathlib import Path

from core.edge_actions.memory_trace import MemoryTrace
from core.edge_actions.models import Observation
from core.edge_actions.task_catalog import get_task


class MemoryTraceTests(unittest.TestCase):
    def test_trace_serialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace = MemoryTrace(Path(tmp))
            obs = Observation(
                url="https://example.com",
                title="Example",
                visible_text="hello",
                interactive_elements=[],
                downloads=[],
                active_tab="Example",
                timestamp="2026-01-01T00:00:00",
                error_state=None,
            )
            trace.add_observation("before", obs)
            out_path = trace.finalize(get_task("company_research"), "completed")
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "completed")


if __name__ == "__main__":
    unittest.main()
