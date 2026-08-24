"""Print a non-mutating compatibility report for one downloaded Octane archive."""

from __future__ import annotations

import argparse
import json

from hermes_houdini.plugin_audit import audit_octane_archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--houdini-build", required=True)
    parser.add_argument("--license-mode", required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            audit_octane_archive(
                arguments.archive,
                target_houdini_build=arguments.houdini_build,
                license_mode=arguments.license_mode,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
