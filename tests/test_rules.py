import json
import tempfile
import unittest
from pathlib import Path

from prompt_asset_inventory.rules import DEFAULT_REQUIRED_FIELDS, InventoryRules


class RulesTest(unittest.TestCase):
    def test_default_required_fields(self):
        rules = InventoryRules()
        self.assertEqual(rules.required_fields, DEFAULT_REQUIRED_FIELDS)

    def test_load_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(json.dumps({"required_fields": ["owner", "purpose"]}), encoding="utf-8")
            rules = InventoryRules.load(str(path))
        self.assertEqual(rules.required_fields, ["owner", "purpose"])

    def test_load_ignore_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(json.dumps({"ignore_paths": ["dist/**"]}), encoding="utf-8")
            rules = InventoryRules.load(str(path))
        self.assertTrue(rules.ignored("dist/file.md"))
        self.assertFalse(rules.ignored("src/file.md"))

    def test_path_defaults_match(self):
        rules = _load_from_dict_for_test(
            {"path_defaults": [{"path": "prompts/**", "metadata": {"owner": "team-a", "source": "registry"}}]}
        )
        self.assertEqual(rules.metadata_defaults_for("prompts/a.md")["owner"], "team-a")

    def test_severity_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(json.dumps({"severity": {"pii": "error"}}), encoding="utf-8")
            rules = InventoryRules.load(str(path))
        self.assertEqual(rules.severity_for("pii"), "error")

    def test_invalid_required_fields_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(json.dumps({"required_fields": "owner"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                InventoryRules.load(str(path))


def _load_from_dict_for_test(data):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return InventoryRules.load(str(path))

if __name__ == "__main__":
    unittest.main()
