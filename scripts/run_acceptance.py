"""Plan or explicitly run tiered Hermes/Houdini acceptance evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hermes_houdini import has_hou
from hermes_houdini.acceptance import (
    DEFAULT_BUDGETS,
    TIER_IDS,
    AcceptanceRequest,
    AcceptanceRunner,
    plan_tiers,
)
from hermes_houdini.acceptance.integrated import (
    IntegratedAcceptanceAdapter,
    runtime_identity,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-tiers", action="store_true", help="list tier IDs and default budgets")
    mode.add_argument("--plan", action="store_true", help="print a non-executing tier plan")
    mode.add_argument("--execute", action="store_true", help="run only explicitly selected tiers")
    parser.add_argument("--tier", action="append", choices=TIER_IDS, default=[])
    parser.add_argument("--artifact-root", help="explicit absolute root for tier artifacts")
    parser.add_argument("--fixture-name", default="HERMES_ACCEPTANCE_G001I")
    parser.add_argument("--allow-pdg-child", action="store_true")
    parser.add_argument("--allow-simulation", action="store_true")
    parser.add_argument("--allow-viewport", action="store_true")
    parser.add_argument("--allow-karma", action="store_true")
    return parser


def _list_tiers() -> dict[str, object]:
    return {
        "schema": "hermes.houdini.acceptance.tiers.v1",
        "tiers": [
            {"id": tier, "default_budget": DEFAULT_BUDGETS[tier]} for tier in TIER_IDS
        ],
    }


def _granted_authorizations(arguments: argparse.Namespace) -> list[str]:
    granted = []
    if arguments.allow_pdg_child:
        granted.append("pdg-child:external_process")
    if arguments.allow_simulation:
        granted.append("simulation:simulation")
    if arguments.allow_viewport:
        granted.append("viewport:interactive_viewport")
    if arguments.allow_karma:
        granted.extend(("karma:render", "karma:external_process"))
    return granted


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
            result["approvals_granted"] = _granted_authorizations(arguments)
            result["artifact_root"] = request.artifact_root
            result["budgets"] = {
                tier: request.budget_for(tier, DEFAULT_BUDGETS[tier])
                for tier in result["required_tiers"]
            }
            print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
            return 0
        required = tuple(plan_tiers(request.tiers)["required_tiers"])
        if any(tier != "pure" for tier in required) and not has_hou():
            parser.error("live tiers require this entry point to run with Houdini Hython")
        root = Path(request.artifact_root)
        if root.exists():
            parser.error("--execute requires an unused artifact-root")
        root.mkdir(parents=True, exist_ok=False)
        adapter = IntegratedAcceptanceAdapter(
            repository_root=Path(__file__).parents[1],
            fixture_name=arguments.fixture_name,
            allow_pdg_child=arguments.allow_pdg_child,
            allow_simulation=arguments.allow_simulation,
            allow_viewport=arguments.allow_viewport,
            allow_karma=arguments.allow_karma,
        )
        adapters = {tier: adapter for tier in required if tier == "pure" or has_hou()}
        build, license_mode, package_inventory = runtime_identity(Path(__file__).parents[1])
        summary = AcceptanceRunner(adapters=adapters).execute(
            request,
            build=build,
            license_mode=license_mode,
            package_inventory=package_inventory,
        )
        payload = summary.as_dict()
        summary_path = root / "acceptance-summary.json"
        with summary_path.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
        return 0 if summary.overall_status in {"pass", "warn"} else 2
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
