"""Plan or explicitly run tiered Hermes/Houdini acceptance evidence."""

from __future__ import annotations

import argparse
import json
import sys

from hermes_houdini.acceptance import (
    DEFAULT_BUDGETS,
    TIER_IDS,
    AcceptanceRequest,
    AcceptanceRunner,
    plan_tiers,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-tiers", action="store_true", help="list tier IDs and default budgets")
    mode.add_argument("--plan", action="store_true", help="print a non-executing tier plan")
    mode.add_argument("--execute", action="store_true", help="run only explicitly selected tiers")
    parser.add_argument("--tier", action="append", choices=TIER_IDS, default=[])
    parser.add_argument("--artifact-root", help="explicit absolute root for tier artifacts")
    return parser


def _list_tiers() -> dict[str, object]:
    return {
        "schema": "hermes.houdini.acceptance.tiers.v1",
        "tiers": [
            {"id": tier, "default_budget": DEFAULT_BUDGETS[tier]} for tier in TIER_IDS
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    if not any((arguments.list_tiers, arguments.plan, arguments.execute)):
        parser.print_help()
        return 0
    if arguments.list_tiers:
        print(json.dumps(_list_tiers(), indent=2, sort_keys=True, allow_nan=False))
        return 0
    if not arguments.tier:
        parser.error("--plan and --execute require at least one explicit --tier")
    if not arguments.artifact_root:
        parser.error("--plan and --execute require an explicit --artifact-root")
    try:
        request = AcceptanceRequest(
            tiers=tuple(arguments.tier), artifact_root=arguments.artifact_root
        )
        if arguments.plan:
            result = plan_tiers(request.tiers)
            result["artifact_root"] = request.artifact_root
            result["budgets"] = {
                tier: request.budget_for(tier, DEFAULT_BUDGETS[tier])
                for tier in result["required_tiers"]
            }
            print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
            return 0
        summary = AcceptanceRunner().execute(request)
        print(json.dumps(summary.as_dict(), indent=2, sort_keys=True, allow_nan=False))
        return 0 if summary.overall_status in {"pass", "warn"} else 2
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
