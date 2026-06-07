from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


DEFAULT_REQUIRED_FIELDS = ["owner", "purpose", "version", "privacy", "source", "citations"]


@dataclass(frozen=True)
class PathDefault:
    pattern: str
    metadata: Dict[str, str]


@dataclass
class InventoryRules:
    required_fields: List[str] = field(default_factory=lambda: list(DEFAULT_REQUIRED_FIELDS))
    ignore_paths: List[str] = field(default_factory=list)
    path_defaults: List[PathDefault] = field(default_factory=list)
    severity: Dict[str, str] = field(
        default_factory=lambda: {
            "missing_required": "warning",
            "pii": "warning",
            "secret": "error",
        }
    )
    max_snippet_chars: int = 280

    @classmethod
    def load(cls, path: str | None) -> "InventoryRules":
        if not path:
            return cls()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ValueError("Rules JSON must be an object.")

        rules = cls()
        if "required_fields" in data:
            rules.required_fields = _string_list(data["required_fields"], "required_fields")
        if "ignore_paths" in data:
            rules.ignore_paths = _string_list(data["ignore_paths"], "ignore_paths")
        if "max_snippet_chars" in data:
            rules.max_snippet_chars = max(80, int(data["max_snippet_chars"]))
        if "severity" in data:
            if not isinstance(data["severity"], Mapping):
                raise ValueError("severity must be an object.")
            rules.severity.update({str(k): str(v) for k, v in data["severity"].items()})
        if "path_defaults" in data:
            rules.path_defaults = _path_defaults(data["path_defaults"])
        return rules

    def ignored(self, relative_path: str) -> bool:
        normalized = relative_path.replace("\\", "/")
        return any(fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(f"./{normalized}", pattern) for pattern in self.ignore_paths)

    def metadata_defaults_for(self, relative_path: str) -> Dict[str, str]:
        normalized = relative_path.replace("\\", "/")
        defaults: Dict[str, str] = {}
        for entry in self.path_defaults:
            if fnmatch.fnmatch(normalized, entry.pattern) or fnmatch.fnmatch(f"./{normalized}", entry.pattern):
                defaults.update(entry.metadata)
        return defaults

    def severity_for(self, category: str) -> str:
        return self.severity.get(category, "warning")


def _string_list(value: object, field_name: str) -> List[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings.")
    return [item.strip().lower() for item in value if item.strip()]


def _path_defaults(value: object) -> List[PathDefault]:
    if not isinstance(value, list):
        raise ValueError("path_defaults must be a list.")
    entries: List[PathDefault] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"path_defaults[{index}] must be an object.")
        pattern = str(item.get("path", "")).strip()
        metadata = item.get("metadata", {})
        if not pattern or not isinstance(metadata, Mapping):
            raise ValueError(f"path_defaults[{index}] needs path and metadata.")
        entries.append(PathDefault(pattern=pattern, metadata={str(k).lower(): str(v) for k, v in metadata.items()}))
    return entries


def supported_rule_fields() -> Iterable[str]:
    return DEFAULT_REQUIRED_FIELDS
