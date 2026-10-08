import asyncio
import os
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.database import migrate_database
from app.database_backup import create_database_backup
from app.deployment_preflight import collect_deployment_readiness


def settings(database, **changes) -> Settings:
    options = {
        "bot_token": "123456789:example-test-secret",
        "environment": "production",
        "city_slug": "saint-petersburg",
        "database_path": str(database),
    }
    options.update(changes)
    return Settings(**options)


def test_production_preflight_accepts_consistent_recent_snapshot(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "live.db"
        backup = tmp_path / "backups" / "snapshot.db"
        await migrate_database(source)
        await create_database_backup(source, backup)
        result = await collect_deployment_readiness(settings(source), backup)
        assert result.status == "ready"
        assert result.environment == "production"
        assert result.catalogs >= 32
        assert result.schema_version >= 1
        assert result.backup_size_bytes > 0
        serialized = repr(asdict(result))
        assert "example-test-secret" not in serialized
        assert str(source) not in serialized
        assert str(backup) not in serialized

    asyncio.run(scenario())


def test_preflight_rejects_nonproduction_and_absent_backup(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "live.db"
        await migrate_database(source)
        with pytest.raises(RuntimeError, match="PLACES_ENVIRONMENT"):
            await collect_deployment_readiness(
                settings(source, environment="development"), tmp_path / "backup.db",
            )
        with pytest.raises(RuntimeError, match="does not exist"):
            await collect_deployment_readiness(settings(source), tmp_path / "missing.db")
        with pytest.raises(ValueError, match="must not be the live"):
            await collect_deployment_readiness(settings(source), source)

    asyncio.run(scenario())


def test_preflight_rejects_stale_and_future_backup(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "live.db"
        backup = tmp_path / "snapshot.db"
        await migrate_database(source)
        await create_database_backup(source, backup)
        stale = (datetime.now(UTC) - timedelta(hours=30)).timestamp()
        os.utime(backup, (stale, stale))
        with pytest.raises(RuntimeError, match="too old"):
            await collect_deployment_readiness(settings(source), backup)
        future = (datetime.now(UTC) + timedelta(hours=2)).timestamp()
        os.utime(backup, (future, future))
        with pytest.raises(RuntimeError, match="in the future"):
            await collect_deployment_readiness(settings(source), backup)

    asyncio.run(scenario())


def test_preflight_rejects_corruption_and_unknown_city(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "live.db"
        backup = tmp_path / "snapshot.db"
        await migrate_database(source)
        await create_database_backup(source, backup)
        backup.write_bytes(b"not a sqlite backup")
        with pytest.raises(RuntimeError, match="integrity"):
            await collect_deployment_readiness(settings(source), backup)
        await create_database_backup(source, backup)
        with pytest.raises(RuntimeError, match="Unsupported city"):
            await collect_deployment_readiness(
                settings(source, city_slug="unknown-city"), backup,
            )
        with pytest.raises(RuntimeError, match="city catalog count"):
            await collect_deployment_readiness(settings(source), backup, min_cities=999)

    asyncio.run(scenario())


def test_preflight_does_not_mutate_live_or_snapshot(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "live.db"
        backup = tmp_path / "snapshot.db"
        await migrate_database(source)
        await create_database_backup(source, backup)
        before = backup.read_bytes()
        await collect_deployment_readiness(settings(source), backup)
        assert backup.read_bytes() == before
        assert source.exists()
        assert tuple(tmp_path.glob(".*.tmp")) == ()

    asyncio.run(scenario())


def test_preflight_rejects_nonsensical_limits(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path / "missing.db")
        with pytest.raises(ValueError, match="max_age_hours"):
            await collect_deployment_readiness(config, "missing.db", max_age_hours=0)
        with pytest.raises(ValueError, match="min_cities"):
            await collect_deployment_readiness(config, "missing.db", min_cities=0)

    asyncio.run(scenario())
