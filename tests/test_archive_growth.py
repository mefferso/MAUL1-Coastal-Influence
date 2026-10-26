import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.archive_growth import build_report


class ArchiveGrowthTests(unittest.TestCase):
    def test_report_distinguishes_tree_history_and_reports_cycle_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            archive = root / "site/data/prospective"
            archive.mkdir(parents=True)
            (archive / "issue.json").write_text("x" * 1000)
            (root / "README.md").write_text("small")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
            (archive / "next.json").write_text("y" * 300)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "data: archive Phase 6 prospective cycle"], cwd=root, check=True)

            report = build_report(root)

        self.assertIn("Working tree:", report)
        self.assertIn("Git pack/history:", report)
        self.assertIn("trailing 7 days:", report)
        self.assertIn("Phase 6 cycle additions:", report)
        self.assertIn("12 months", report)


if __name__ == "__main__":
    unittest.main()
