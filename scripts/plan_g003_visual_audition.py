"""Write the deterministic, no-side-effect G003 Gate V audition manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hermes_houdini.g003_visual_audition import (
    build_visual_audition_manifest,
    visual_audition_manifest_sha256,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--runtime-status", required=True)
    parser.add_argument("--runtime-detail", required=True)
    arguments = parser.parse_args()
    output = Path(arguments.output).expanduser().resolve()
    if output.suffix.lower() != ".json" or not output.is_absolute():
        raise ValueError("--output must be an absolute .json path")
    if output.exists():
        raise FileExistsError(f"refusing existing dry manifest: {output}")
    manifest = build_visual_audition_manifest(
        project_root=arguments.project_root,
        artifact_root=arguments.artifact_root,
        source_identity={
            "commit": arguments.source_commit,
            "branch": arguments.source_branch,
            "dirty": False,
        },
        runtime_observation={
            "status": arguments.runtime_status,
            "detail": arguments.runtime_detail,
            "mutation_performed": False,
        },
    )
    digest = visual_audition_manifest_sha256(manifest)
    manifest["approval"]["manifest_sha256_subject"] = digest
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"manifest": str(output), "sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
