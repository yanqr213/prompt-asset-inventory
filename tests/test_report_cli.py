import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from prompt_asset_inventory.cli import main
from prompt_asset_inventory.inventory import scan
from prompt_asset_inventory.report import render_csv, render_json, render_markdown


class ReportCliTest(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "prompt.md").write_text(
            "owner: team\npurpose: test\nversion: 1\nprivacy: none\nsource: local\ncitations: none\nSystem prompt:\nBe useful.",
            encoding="utf-8",
        )
        return tmp, root

    def test_render_json_contains_assets(self):
        tmp, root = self.make_repo()
        with tmp:
            data = json.loads(render_json(scan(root)))
        self.assertEqual(data["asset_count"], 1)
        self.assertEqual(len(data["assets"]), 1)

    def test_render_csv_header_and_row(self):
        tmp, root = self.make_repo()
        with tmp:
            rows = list(csv.DictReader(io.StringIO(render_csv(scan(root)))))
        self.assertEqual(rows[0]["owner"], "team")
        self.assertEqual(rows[0]["type"], "system_prompt")

    def test_render_markdown_has_summary(self):
        tmp, root = self.make_repo()
        with tmp:
            text = render_markdown(scan(root))
        self.assertIn("# Prompt Asset Inventory", text)
        self.assertIn("Assets found: 1", text)

    def test_cli_writes_output(self):
        tmp, root = self.make_repo()
        with tmp:
            output = root / "out.json"
            code = main([str(root), "--format", "json", "--output", str(output)])
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(data["asset_count"], 1)

    def test_cli_check_passes_for_complete_metadata(self):
        tmp, root = self.make_repo()
        with tmp:
            code = main([str(root), "--check", "--output", str(root / "out.md")])
        self.assertEqual(code, 0)

    def test_cli_check_fails_for_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prompt.md").write_text("System prompt:\nMissing fields.", encoding="utf-8")
            code = main([str(root), "--check", "--output", str(root / "out.md")])
        self.assertEqual(code, 1)

    def test_cli_fail_on_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = main([str(root), "--check", "--fail-on-empty", "--output", str(root / "out.md")])
        self.assertEqual(code, 1)

    def test_cli_invalid_root_returns_two(self):
        code = main(["Z:/definitely/not/here"])
        self.assertEqual(code, 2)

    def test_cli_csv_format(self):
        tmp, root = self.make_repo()
        with tmp:
            output = root / "out.csv"
            code = main([str(root), "--format", "csv", "--output", str(output)])
            text = output.read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertIn("finding_codes", text)

    def test_markdown_no_assets_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = render_markdown(scan(tmp))
        self.assertIn("No prompt-like assets", text)


if __name__ == "__main__":
    unittest.main()
