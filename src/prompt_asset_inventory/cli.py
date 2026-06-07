from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .inventory import scan
from .report import render
from .rules import InventoryRules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt-asset-inventory",
        description="Offline inventory scanner for prompt assets in AI and developer tooling repositories.",
    )
    parser.add_argument("root", nargs="?", default=".", help="Repository or directory to scan.")
    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "json", "csv"],
        default="markdown",
        help="Output format. Default: markdown.",
    )
    parser.add_argument("-o", "--output", help="Write the inventory report to a file.")
    parser.add_argument("--rules", help="Optional inventory rules JSON file.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when warning/error findings are present; otherwise exit 0.",
    )
    parser.add_argument(
        "--fail-on-empty",
        action="store_true",
        help="In check mode, exit 1 when no prompt assets are found.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        rules = InventoryRules.load(args.rules)
        result = scan(args.root, rules)
        rendered = render(result, args.format)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(rendered)
        else:
            sys.stdout.write(rendered)
        if args.check and (result.failed or (args.fail_on_empty and not result.assets)):
            return 1
        return 0
    except Exception as exc:
        print(f"prompt-asset-inventory: {exc}", file=sys.stderr)
        return 2
