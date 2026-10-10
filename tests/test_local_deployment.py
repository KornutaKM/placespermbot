import asyncio
from dataclasses import asdict
from pathlib import Path

import pytest

from app.config import Settings
from app.database import migrate_database
from app.database_backup import create_database_backup
from app.deployment_preflight import collect_deployment_readiness

SHA = "a" * 40


def make_settings(database: Path, *, environment: str = "development") -> Settings:
    return Settings(
        bot_token="123456789:local-release-test",
        environment=environment,
        city_slug="perm",
        database_path=str(database),
        build_sha=SHA,
    )


def test_local_readiness_accepts_valid_snapshot_without_mutation(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "places.db"
        backup = tmp_path / "backups" / "snapshot.db"
        await migrate_database(source)
        await create_database_backup(source, backup)
        before = backup.read_bytes()

        result = await collect_deployment_readiness(
            make_settings(source),
            backup,
            expected_sha=SHA,
            required_environment="development",
        )

        assert result.status == "ready"
        assert result.environment == "development"
        assert result.build_sha == SHA
        assert result.catalogs >= 35
        assert result.backup_size_bytes > 0
        assert backup.read_bytes() == before
        serialized = repr(asdict(result))
        assert "local-release-test" not in serialized
        assert str(source) not in serialized
        assert str(backup) not in serialized

    asyncio.run(scenario())


def test_local_preflight_rejects_production_and_mismatched_build(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "places.db"
        backup = tmp_path / "backup.db"
        await migrate_database(source)
        await create_database_backup(source, backup)

        with pytest.raises(RuntimeError, match="PLACES_ENVIRONMENT=development"):
            await collect_deployment_readiness(
                make_settings(source, environment="production"),
                backup,
                expected_sha=SHA,
                required_environment="development",
            )

        with pytest.raises(RuntimeError, match="revision"):
            await collect_deployment_readiness(
                make_settings(source),
                backup,
                expected_sha="b" * 40,
                required_environment="development",
            )

    asyncio.run(scenario())


def test_production_preflight_still_rejects_local_environment(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "places.db"
        backup = tmp_path / "backup.db"
        await migrate_database(source)
        await create_database_backup(source, backup)

        with pytest.raises(RuntimeError, match="PLACES_ENVIRONMENT=production"):
            await collect_deployment_readiness(
                make_settings(source),
                backup,
                expected_sha=SHA,
            )
        with pytest.raises(ValueError, match="unsupported preflight environment"):
            await collect_deployment_readiness(
                make_settings(source),
                backup,
                expected_sha=SHA,
                required_environment="ci",
            )

    asyncio.run(scenario())


def test_windows_batch_updater_has_required_release_gates() -> None:
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "update-local.ps1"
    ).read_text(encoding="utf-8")
    for gate in (
        "git fetch origin main",
        "git status --porcelain",
        "git merge-base --is-ancestor",
        "docker compose config --quiet",
        "docker compose exec -T bot python -m app.healthcheck",
        "PLACES_ENVIRONMENT",
        "app.database_backup",
        "app.local_deployment_preflight",
        "PLACES_BUILD_SHA=",
        "docker compose up -d --no-deps --no-build bot",
        "app.diagnostics",
    ):
        # The environment guard is checked via get_settings() and explicit
        # comparison instead of printing any env-file secret.
        if gate == "PLACES_ENVIRONMENT":
            assert "development-only" in script
        else:
            assert gate in script
    assert script.index("app.database_backup") < script.index("git switch --detach")
    assert script.index("app.local_deployment_preflight") < script.index(
        "docker compose up -d"
    )
    assert "docker compose down -v" not in script
    assert "docker volume rm" not in script
