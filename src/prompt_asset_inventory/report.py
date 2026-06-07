from __future__ import annotations

import csv
import io
import json
from typing import Iterable, List

from .models import Asset, Finding, InventoryResult


def render_json(result: InventoryResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"


def render_csv(result: InventoryResult) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "path",
            "line_start",
            "line_end",
            "type",
            "title",
            "owner",
            "purpose",
            "version",
            "privacy",
            "source",
            "citations",
            "finding_codes",
            "finding_severities",
            "snippet",
        ],
    )
    writer.writeheader()
    for asset in result.assets:
        writer.writerow(
            {
                "id": asset.asset_id,
                "path": asset.path,
                "line_start": asset.line_start,
                "line_end": asset.line_end,
                "type": asset.asset_type,
                "title": asset.title,
                "owner": asset.metadata.get("owner", ""),
                "purpose": asset.metadata.get("purpose", ""),
                "version": asset.metadata.get("version", ""),
                "privacy": asset.metadata.get("privacy", ""),
                "source": asset.metadata.get("source", ""),
                "citations": asset.metadata.get("citations", ""),
                "finding_codes": ";".join(finding.code for finding in asset.findings),
                "finding_severities": ";".join(finding.severity for finding in asset.findings),
                "snippet": asset.snippet,
            }
        )
    return output.getvalue()


def render_markdown(result: InventoryResult) -> str:
    lines: List[str] = [
        "# Prompt Asset Inventory",
        "",
        f"- Root: `{result.root}`",
        f"- Files scanned: {result.files_scanned}",
        f"- Assets found: {len(result.assets)}",
        f"- Findings: {result.finding_count}",
        "",
    ]
    if not result.assets:
        lines.extend(["No prompt-like assets were found.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| ID | Type | Location | Owner | Purpose | Version | Findings |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for asset in result.assets:
        lines.append(
            "| {id} | {type} | {loc} | {owner} | {purpose} | {version} | {findings} |".format(
                id=_escape(asset.asset_id),
                type=_escape(asset.asset_type),
                loc=_escape(f"{asset.path}:{asset.line_start}"),
                owner=_escape(asset.metadata.get("owner", "")),
                purpose=_escape(asset.metadata.get("purpose", "")),
                version=_escape(asset.metadata.get("version", "")),
                findings=_escape(_finding_summary(asset.findings)),
            )
        )
    lines.append("")
    lines.append("## Asset Details")
    lines.append("")
    for asset in result.assets:
        lines.extend(_asset_detail(asset))
    return "\n".join(lines) + "\n"


def render(result: InventoryResult, output_format: str) -> str:
    if output_format == "json":
        return render_json(result)
    if output_format == "csv":
        return render_csv(result)
    if output_format == "markdown":
        return render_markdown(result)
    raise ValueError(f"Unsupported output format: {output_format}")


def _asset_detail(asset: Asset) -> List[str]:
    lines = [
        f"### {asset.asset_id} - {asset.asset_type}",
        "",
        f"- Location: `{asset.path}:{asset.line_start}-{asset.line_end}`",
        f"- Title: {asset.title}",
        f"- Signals: {', '.join(asset.signals) if asset.signals else 'none'}",
        f"- Metadata: {_metadata_summary(asset)}",
        "",
        "Snippet:",
        "",
        f"> {asset.snippet}",
        "",
    ]
    if asset.findings:
        lines.append("Findings:")
        for finding in asset.findings:
            field = f" `{finding.field}`" if finding.field else ""
            lines.append(f"- `{finding.severity}` `{finding.code}`{field}: {finding.message}")
        lines.append("")
    return lines


def _metadata_summary(asset: Asset) -> str:
    if not asset.metadata:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(asset.metadata.items()))


def _finding_summary(findings: Iterable[Finding]) -> str:
    items = [f"{finding.severity}:{finding.code}" for finding in findings]
    return "; ".join(items)


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
