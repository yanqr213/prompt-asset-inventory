from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: str
    field: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field": self.field,
        }


@dataclass
class Asset:
    asset_id: str
    path: str
    line_start: int
    line_end: int
    asset_type: str
    title: str
    snippet: str
    metadata: Dict[str, str] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.asset_id,
            "path": self.path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "type": self.asset_type,
            "title": self.title,
            "snippet": self.snippet,
            "metadata": dict(self.metadata),
            "signals": list(self.signals),
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass
class InventoryResult:
    root: str
    assets: List[Asset]
    files_scanned: int
    files_skipped: int

    @property
    def finding_count(self) -> int:
        return sum(len(asset.findings) for asset in self.assets)

    @property
    def failed(self) -> bool:
        return any(finding.severity in {"error", "warning"} for asset in self.assets for finding in asset.findings)

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "asset_count": len(self.assets),
            "finding_count": self.finding_count,
            "assets": [asset.to_dict() for asset in self.assets],
        }
