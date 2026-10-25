import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class EventWindowTests(unittest.TestCase):
    def test_june_27_to_july_1_transition_is_not_labeled_beryl_forcing(self):
        cases = json.loads((ROOT / "event_windows.json").read_text())
        phases = {phase["id"]: phase for case in cases for phase in case["phases"]}
        transition = phases["transition_unattributed"]
        beryl = phases["beryl_gulf_approach_landfall"]
        self.assertEqual(transition["start_utc"], "2024-06-27T00:00:00Z")
        self.assertEqual(transition["end_utc"], "2024-07-01T00:00:00Z")
        self.assertEqual(transition["attribution"], "unresolved")
        self.assertEqual(beryl["start_utc"], "2024-07-05T00:00:00Z")
        self.assertGreaterEqual(beryl["start_utc"], transition["end_utc"])

    def test_windows_are_half_open_and_never_overlap_within_each_case(self):
        cases = json.loads((ROOT / "event_windows.json").read_text())
        for case in cases:
            phases = sorted(case["phases"], key=lambda phase: phase["start_utc"])
            for left, right in zip(phases, phases[1:]):
                self.assertLessEqual(left["end_utc"], right["start_utc"], case["id"])


if __name__ == "__main__":
    unittest.main()
