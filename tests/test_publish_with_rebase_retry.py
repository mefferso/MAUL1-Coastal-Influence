"""Exercise the shared GitHub Actions publisher against concurrent writers."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / ".github/scripts/publish-with-rebase-retry.sh"


def run(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=check)


class PublishWithRebaseRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        run(["git", "init", "--bare", "--initial-branch=main", str(self.remote)], self.root)
        self.writer = self.clone("writer")
        self.racer = self.clone("racer")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def clone(self, name: str) -> Path:
        path = self.root / name
        run(["git", "clone", str(self.remote), str(path)], self.root)
        run(["git", "config", "user.name", name], path)
        run(["git", "config", "user.email", f"{name}@example.test"], path)
        return path

    def seed(self, text: str) -> None:
        (self.writer / "shared.txt").write_text(text, encoding="utf-8")
        run(["git", "add", "shared.txt"], self.writer)
        run(["git", "commit", "-m", "seed"], self.writer)
        run(["git", "push", "origin", "main"], self.writer)
        run(["git", "fetch", "origin", "main"], self.racer)
        run(["git", "checkout", "-B", "main", "origin/main"], self.racer)

    def publish(self) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "Actions bot"
        env["GIT_AUTHOR_EMAIL"] = "actions@example.test"
        env["GIT_COMMITTER_NAME"] = "Actions bot"
        env["GIT_COMMITTER_EMAIL"] = "actions@example.test"
        return subprocess.run(
            ["bash", str(PUBLISHER), "main", "automated update"], cwd=self.writer,
            text=True, capture_output=True, env=env, check=False,
        )

    def test_rebases_and_pushes_after_concurrent_unrelated_commit(self) -> None:
        self.seed("base\n")
        (self.writer / "writer.txt").write_text("writer\n", encoding="utf-8")
        (self.racer / "racer.txt").write_text("racer\n", encoding="utf-8")
        run(["git", "add", "racer.txt"], self.racer)
        run(["git", "commit", "-m", "concurrent change"], self.racer)
        run(["git", "push", "origin", "main"], self.racer)
        run(["git", "add", "writer.txt"], self.writer)

        result = self.publish()

        self.assertEqual(result.returncode, 0, result.stderr)
        run(["git", "fetch", "origin", "main"], self.writer)
        files = run(["git", "ls-tree", "-r", "--name-only", "origin/main"], self.writer).stdout.splitlines()
        self.assertEqual(set(files), {"shared.txt", "racer.txt", "writer.txt"})

    def test_reports_rebase_conflict_and_leaves_remote_unchanged(self) -> None:
        self.seed("same line\n")
        (self.writer / "shared.txt").write_text("writer version\n", encoding="utf-8")
        (self.racer / "shared.txt").write_text("racer version\n", encoding="utf-8")
        run(["git", "add", "shared.txt"], self.racer)
        run(["git", "commit", "-m", "concurrent conflicting change"], self.racer)
        run(["git", "push", "origin", "main"], self.racer)
        run(["git", "add", "shared.txt"], self.writer)

        result = self.publish()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Rebase conflict", result.stderr)
        remote_text = run(["git", "show", "origin/main:shared.txt"], self.racer).stdout
        self.assertEqual(remote_text, "racer version\n")


if __name__ == "__main__":
    unittest.main()
