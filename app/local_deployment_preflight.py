"""Fail-closed, read-only checks for operator-initiated local Docker updates.

Production deployments must continue to use app.deployment_preflight.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from app.config import get_settings
from app.deployment_preflight import collect_deployment_readiness


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--max-age-hours", type=float, default=24)
    args = parser.parse_args()

    readiness = asyncio.run(
        collect_deployment_readiness(
            get_settings(),
            args.backup,
            expected_sha=args.expected_sha,
            max_age_hours=args.max_age_hours,
            required_environment="development",
        )
    )
    print(json.dumps(asdict(readiness), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
