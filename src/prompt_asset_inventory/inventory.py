from __future__ import annotations

from pathlib import Path

from .detect import SUPPORTED_EXTENSIONS, detect_assets, iter_candidate_files
from .models import InventoryResult
from .rules import InventoryRules


def scan(root: str | Path, rules: InventoryRules | None = None) -> InventoryResult:
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Scan root does not exist: {root_path}")
    active_rules = rules or InventoryRules()
    assets = []
    files_scanned = 0
    if root_path.is_file():
        if root_path.suffix.lower() in SUPPORTED_EXTENSIONS and not active_rules.ignored(root_path.name):
            files_scanned = 1
            assets.extend(detect_assets(root_path, root_path.parent, active_rules))
    elif root_path.is_dir():
        for path in iter_candidate_files(root_path, active_rules):
            files_scanned += 1
            assets.extend(detect_assets(path, root_path, active_rules))
    else:
        raise NotADirectoryError(f"Scan root is not a file or directory: {root_path}")

    return InventoryResult(
        root=str(root_path),
        assets=assets,
        files_scanned=files_scanned,
        files_skipped=0,
    )
