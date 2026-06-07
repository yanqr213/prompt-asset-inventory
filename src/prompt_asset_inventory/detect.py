from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .models import Asset, Finding
from .rules import InventoryRules

SUPPORTED_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
}

SIGNALS: Sequence[Tuple[str, re.Pattern[str]]] = (
    ("system_prompt", re.compile(r"\b(system|developer)\s*(prompt|message|instruction)s?\b", re.I)),
    ("role_message", re.compile(r"\b[\"']?(role|speaker)[\"']?\s*[:=]\s*[\"']?(system|user|assistant|developer)\b", re.I)),
    ("few_shot", re.compile(r"\b(few[-_\s]?shot|example\s*(conversation|prompt|case)s?)\b", re.I)),
    ("agent_instructions", re.compile(r"\b(agent|assistant|cursor|codex|claude)\s*(instruction|rule|policy|persona)s?\b", re.I)),
    ("tool_schema", re.compile(r"\b(tool|function)\s*(schema|description|definition|parameters?)s?\b", re.I)),
    ("eval_case", re.compile(r"\b(eval|evaluation|golden|expected[_\s-]?output|rubric|test[_\s-]?case)\b", re.I)),
    ("prompt_variable", re.compile(r"\b([A-Z0-9_]*PROMPT|prompt|instructions?|messages?)\b", re.I)),
)

METADATA_RE = re.compile(
    r"^\s*(?:[#*/\-]+\s*)?[\"']?(owner|purpose|version|privacy|source|citations?)[\"']?\s*[:=]\s*(.+?)\s*$",
    re.I,
)

SECRET_PATTERNS: Sequence[Tuple[str, re.Pattern[str]]] = (
    ("secret_openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("secret_github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("secret_aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("secret_private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("secret_assignment", re.compile(r"\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I)),
)

PII_PATTERNS: Sequence[Tuple[str, re.Pattern[str]]] = (
    ("pii_email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("pii_phone", re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")),
    ("pii_ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("pii_credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
)


def iter_candidate_files(root: Path, rules: InventoryRules) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if rules.ignored(relative):
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def detect_assets(path: Path, root: Path, rules: InventoryRules) -> List[Asset]:
    text = _read_text(path)
    if text is None:
        return []
    relative = path.relative_to(root).as_posix()
    lines = text.splitlines()
    windows = _candidate_windows(lines, path.suffix.lower())
    assets: List[Asset] = []
    seen = set()
    for start, end, signals in windows:
        key = (start, end, tuple(sorted(signals)))
        if key in seen:
            continue
        seen.add(key)
        block = "\n".join(lines[start - 1 : end])
        metadata = rules.metadata_defaults_for(relative)
        metadata.update(extract_metadata(block))
        asset_type = classify(signals, block)
        title = _title_for(block, asset_type)
        snippet = _snippet(block, rules.max_snippet_chars)
        asset = Asset(
            asset_id=_asset_id(relative, start, asset_type, block),
            path=relative,
            line_start=start,
            line_end=end,
            asset_type=asset_type,
            title=title,
            snippet=snippet,
            metadata=metadata,
            signals=sorted(signals),
        )
        asset.findings = evaluate_asset(asset, rules, block)
        assets.append(asset)
    return assets


def extract_metadata(text: str) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for line in text.splitlines():
        match = METADATA_RE.match(line)
        if match:
            key = "citations" if match.group(1).lower().startswith("citation") else match.group(1).lower()
            metadata[key] = _clean_metadata_value(match.group(2))
    return metadata


def classify(signals: Sequence[str], text: str) -> str:
    ordered = [
        ("eval_case", "eval_case"),
        ("tool_schema", "tool_schema"),
        ("few_shot", "few_shot"),
        ("agent_instructions", "agent_instructions"),
        ("system_prompt", "system_prompt"),
        ("role_message", "chat_messages"),
        ("prompt_variable", "prompt"),
    ]
    signal_set = set(signals)
    lower = text.lower()
    for signal, asset_type in ordered:
        if signal in signal_set:
            return asset_type
    if "system" in lower and "assistant" in lower:
        return "chat_messages"
    return "prompt"


def evaluate_asset(asset: Asset, rules: InventoryRules, full_text: str | None = None) -> List[Finding]:
    findings: List[Finding] = []
    text_to_check = full_text if full_text is not None else asset.snippet
    for field in rules.required_fields:
        value = asset.metadata.get(field)
        if not value or value.strip().lower() in {"unknown", "todo", "tbd", "n/a"}:
            findings.append(
                Finding(
                    code="missing_required_metadata",
                    field=field,
                    severity=rules.severity_for("missing_required"),
                    message=f"Missing required metadata: {field}",
                )
            )
    secret_codes = _matched_codes(text_to_check, SECRET_PATTERNS)
    for code in secret_codes:
        findings.append(
            Finding(
                code=code,
                severity=rules.severity_for("secret"),
                message="Prompt asset contains text that looks like a secret or credential.",
            )
        )
    pii_codes = _matched_codes(text_to_check, PII_PATTERNS)
    for code in pii_codes:
        findings.append(
            Finding(
                code=code,
                severity=rules.severity_for("pii"),
                message="Prompt asset contains text that looks like personal data.",
            )
        )
    return findings


def _candidate_windows(lines: Sequence[str], extension: str) -> List[Tuple[int, int, List[str]]]:
    windows: List[Tuple[int, int, List[str]]] = []
    for index, line in enumerate(lines, start=1):
        signals = [name for name, pattern in SIGNALS if pattern.search(line)]
        if not signals:
            continue
        start, end = _expand_window(lines, index, extension)
        block = "\n".join(lines[start - 1 : end])
        extra = [name for name, pattern in SIGNALS if pattern.search(block)]
        windows.append((start, end, sorted(set(signals + extra))))
    return _merge_windows(windows)


def _expand_window(lines: Sequence[str], line_number: int, extension: str) -> Tuple[int, int]:
    if extension in {".json", ".yaml", ".yml"}:
        return _expand_structured(lines, line_number)
    if extension in {".md", ".markdown", ".txt"}:
        return _expand_text_section(lines, line_number)
    return _expand_code_block(lines, line_number)


def _expand_text_section(lines: Sequence[str], line_number: int) -> Tuple[int, int]:
    start = line_number
    while start > 1:
        prev = lines[start - 2]
        if start != line_number and not prev.strip():
            break
        if prev.lstrip().startswith("#") and start != line_number:
            start -= 1
            break
        start -= 1
    end = line_number
    while end < len(lines):
        current = lines[end]
        if end != line_number and not current.strip():
            break
        if end != line_number and current.lstrip().startswith("#"):
            break
        end += 1
    return max(1, start), min(len(lines), end)


def _expand_structured(lines: Sequence[str], line_number: int) -> Tuple[int, int]:
    start = max(1, line_number - 4)
    end = min(len(lines), line_number + 8)
    return start, end


def _expand_code_block(lines: Sequence[str], line_number: int) -> Tuple[int, int]:
    start = line_number
    while start > 1 and lines[start - 2].strip() and not _looks_like_new_assignment(lines[start - 2]):
        start -= 1
    end = line_number
    quote_balance = 0
    while end < len(lines):
        current = lines[end - 1]
        quote_balance += current.count('"""') + current.count("'''")
        if end > line_number and not current.strip() and quote_balance % 2 == 0:
            break
        if end > line_number and _looks_like_new_assignment(current) and quote_balance % 2 == 0:
            end -= 1
            break
        end += 1
    return max(1, start), min(len(lines), end)


def _merge_windows(windows: Sequence[Tuple[int, int, List[str]]]) -> List[Tuple[int, int, List[str]]]:
    merged: List[Tuple[int, int, List[str]]] = []
    for start, end, signals in sorted(windows):
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end, list(signals)))
            continue
        prev_start, prev_end, prev_signals = merged[-1]
        merged[-1] = (prev_start, max(prev_end, end), sorted(set(prev_signals + signals)))
    return merged


def _looks_like_new_assignment(line: str) -> bool:
    return bool(re.match(r"\s*(?:const|let|var)?\s*[A-Za-z_][A-Za-z0-9_]*\s*[:=]", line))


def _read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def _asset_id(relative_path: str, line_start: int, asset_type: str, block: str) -> str:
    digest = hashlib.sha1(f"{relative_path}:{line_start}:{asset_type}:{block}".encode("utf-8")).hexdigest()[:12]
    return f"pai-{digest}"


def _title_for(block: str, asset_type: str) -> str:
    for line in block.splitlines():
        clean = line.strip().strip("# ").strip()
        if clean and not METADATA_RE.match(line):
            return clean[:80]
    return asset_type.replace("_", " ").title()


def _snippet(block: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", block).strip()
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."


def _matched_codes(text: str, patterns: Sequence[Tuple[str, re.Pattern[str]]]) -> List[str]:
    return [code for code, pattern in patterns if pattern.search(text)]


def _clean_metadata_value(value: str) -> str:
    clean = value.strip().rstrip(",").strip()
    return clean.strip("\"'")
