import tempfile
import unittest
from pathlib import Path

from prompt_asset_inventory.detect import classify, detect_assets, extract_metadata
from prompt_asset_inventory.inventory import scan
from prompt_asset_inventory.rules import InventoryRules


class DetectTest(unittest.TestCase):
    def test_extract_plain_metadata(self):
        metadata = extract_metadata("owner: team\npurpose: classify\nversion: 1")
        self.assertEqual(metadata["owner"], "team")
        self.assertEqual(metadata["purpose"], "classify")

    def test_extract_quoted_json_metadata(self):
        metadata = extract_metadata('"owner": "team",\n"citations": "runbook.md"')
        self.assertEqual(metadata["owner"], "team")
        self.assertEqual(metadata["citations"], "runbook.md")

    def test_classify_eval_case(self):
        self.assertEqual(classify(["eval_case"], "eval case"), "eval_case")

    def test_classify_tool_schema(self):
        self.assertEqual(classify(["tool_schema"], "tool schema"), "tool_schema")

    def test_classify_few_shot(self):
        self.assertEqual(classify(["few_shot"], "few-shot example"), "few_shot")

    def test_detect_markdown_system_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "prompt.md"
            path.write_text(
                "# Prompt\nowner: team\npurpose: test\nversion: 1\nprivacy: none\nsource: local\ncitations: none\n\nSystem prompt:\nBe helpful.",
                encoding="utf-8",
            )
            assets = detect_assets(path, root, InventoryRules())
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].asset_type, "system_prompt")
        self.assertFalse(assets[0].findings)

    def test_detect_python_prompt_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "prompts.py"
            path.write_text('SYSTEM_PROMPT = """\nSystem prompt:\nAnswer carefully.\n"""', encoding="utf-8")
            assets = detect_assets(path, root, InventoryRules())
        self.assertEqual(len(assets), 1)
        self.assertIn("system_prompt", assets[0].signals)

    def test_detect_json_role_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "case.json"
            path.write_text('{"messages":[{"role":"system","content":"Follow rules"}]}', encoding="utf-8")
            assets = detect_assets(path, root, InventoryRules())
        self.assertEqual(len(assets), 1)
        self.assertIn(assets[0].asset_type, {"chat_messages", "prompt"})

    def test_missing_metadata_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "prompt.md"
            path.write_text("System prompt:\nDo a task.", encoding="utf-8")
            assets = detect_assets(path, root, InventoryRules())
        fields = {finding.field for finding in assets[0].findings}
        self.assertIn("owner", fields)
        self.assertIn("purpose", fields)

    def test_pii_email_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "prompt.md"
            path.write_text("System prompt:\nContact alice@team.test.", encoding="utf-8")
            assets = detect_assets(path, root, InventoryRules())
        self.assertIn("pii_email", {finding.code for finding in assets[0].findings})

    def test_secret_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "prompt.md"
            path.write_text('System prompt:\napi_key = "abcdef1234567890"', encoding="utf-8")
            assets = detect_assets(path, root, InventoryRules())
        self.assertIn("secret_assignment", {finding.code for finding in assets[0].findings})

    def test_scan_ignores_binary_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.md").write_bytes(b"\x00\x01")
            result = scan(root)
        self.assertEqual(result.assets, [])

    def test_scan_respects_ignore_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ignored = root / "ignored"
            ignored.mkdir()
            (ignored / "prompt.md").write_text("System prompt:\nHidden.", encoding="utf-8")
            rules = InventoryRules()
            rules.ignore_paths = ["ignored/**"]
            result = scan(root, rules)
        self.assertEqual(result.assets, [])

    def test_scan_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.md"
            path.write_text("System prompt:\nOne file.", encoding="utf-8")
            result = scan(path)
        self.assertEqual(result.files_scanned, 1)
        self.assertEqual(len(result.assets), 1)

    def test_path_defaults_fill_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompts = root / "prompts"
            prompts.mkdir()
            path = prompts / "a.md"
            path.write_text("purpose: test\nSystem prompt:\nDo it.", encoding="utf-8")
            rules = _load_rules({"path_defaults": [{"path": "prompts/**", "metadata": {"owner": "team"}}]})
            assets = detect_assets(path, root, rules)
        self.assertEqual(assets[0].metadata["owner"], "team")


def _load_rules(data):
    import json

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return InventoryRules.load(str(path))


if __name__ == "__main__":
    unittest.main()
