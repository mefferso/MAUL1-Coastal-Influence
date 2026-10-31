import pathlib
import unittest


ROOT=pathlib.Path(__file__).resolve().parents[1]


class TestArchiveWorkflow(unittest.TestCase):
    def test_archive_report_and_safe_publisher_are_wired(self):
        workflow=(ROOT/".github/workflows/forcing-archive.yml").read_text()
        self.assertIn("cron: '43 * * * *'", workflow)
        self.assertIn("python scripts/archive_completeness.py --summary", workflow)
        self.assertIn(".github/scripts/publish-with-rebase-retry.sh main", workflow)
        self.assertIn("tests.test_archive_completeness", workflow)
        self.assertIn("tests.test_archive_workflow", workflow)

    def test_archive_only_pushes_skip_pages_and_mrms_stays_out_of_collection(self):
        site=(ROOT/".github/workflows/site.yml").read_text()
        workflow=(ROOT/".github/workflows/forcing-archive.yml").read_text()
        self.assertIn("paths-ignore:", site)
        self.assertIn("research/prospective-forcing-archive/**", site)
        collection=workflow.split("  collect-and-persist:",1)[1]
        self.assertNotIn("collect_mrms_basin_qpe.py", collection)


if __name__ == "__main__":
    unittest.main()
