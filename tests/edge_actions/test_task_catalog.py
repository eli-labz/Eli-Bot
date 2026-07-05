import unittest

from core.edge_actions.task_catalog import load_task_specs


class TaskCatalogTests(unittest.TestCase):
    def test_catalog_has_at_least_100_tasks(self):
        specs = load_task_specs()
        self.assertGreaterEqual(len(specs), 100)

    def test_every_task_has_required_fields(self):
        specs = load_task_specs()
        for task in specs.values():
            self.assertTrue(task.success_criteria)
            self.assertTrue(task.allowed_actions)
            self.assertTrue(task.approval_required_actions)
            self.assertTrue(task.verification_steps)
            self.assertTrue(task.recovery_behavior)
            self.assertTrue(task.timeout_behavior)


if __name__ == "__main__":
    unittest.main()
