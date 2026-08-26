from __future__ import annotations

from pathlib import Path

from hermes_houdini.acceptance.integrated import IntegratedAcceptanceAdapter
from hermes_houdini.acceptance.runner import AcceptanceRunner
from hermes_houdini.acceptance.schema import AcceptanceRequest


class _IntegratedRoute:
    def __init__(self, live: IntegratedAcceptanceAdapter) -> None:
        self.live = live

    def run(self, *, tier, artifact_root, budget):
        if tier == "pure":
            return {
                "tier": "pure",
                "status": "pass",
                "command": ["integration-test", "pure-fixture"],
                "started_at": "2026-08-25T00:00:00Z",
                "duration_seconds": 0.0,
                "budget": budget,
                "observed": {"fixture": True},
                "artifacts": [],
                "warnings": [],
                "errors": [],
            }
        return self.live.run(tier=tier, artifact_root=artifact_root, budget=budget)


def test_integrated_runner_reaches_single_frame_with_compatibility_and_baseline(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).parents[2]
    live = IntegratedAcceptanceAdapter(
        repository_root=repository,
        fixture_name=f"G001I_{tmp_path.name[-12:].replace('-', '_')}",
    )
    route = _IntegratedRoute(live)
    request = AcceptanceRequest(
        tiers=("single-frame",), artifact_root=str(tmp_path / "acceptance")
    )
    runner = AcceptanceRunner(
        adapters={
            "pure": route,
            "hython-read": route,
            "graph-edit": route,
            "single-frame": route,
        }
    )

    summary = runner.execute(request, build="22.0.368", license_mode="Apprentice")

    assert summary.overall_status == "pass"
    by_tier = {item.tier: item for item in summary.results}
    assert by_tier["hython-read"].observed["compatibility"]["status"] == "pass"
    assert by_tier["single-frame"].observed["resource_baseline"]["status"] == "pass"
    graph_artifact = by_tier["graph-edit"].artifacts[0]
    assert graph_artifact["sha256"]
    assert Path(graph_artifact["path"]).is_file()
