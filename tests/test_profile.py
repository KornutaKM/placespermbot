import asyncio

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.database import migrate_database
from app.planner import INTEREST_LABELS
from app.profile import build_profile_summary, profile_text
from app.storage import FavoritesRepository, InterestsRepository, VisitedRepository


def test_profile_summary_is_scoped_by_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)

        favorites = FavoritesRepository(database_path)
        interests = InterestsRepository(database_path)
        visited = VisitedRepository(database_path)

        await favorites.add(1, CITY_SLUG, "hermitage")
        await favorites.add(1, "another-city", "other-place")
        await favorites.add(2, CITY_SLUG, "palace-square")

        await visited.add(1, CITY_SLUG, "summer-garden")
        await visited.add(1, "another-city", "other-place")
        await visited.add(2, CITY_SLUG, "hermitage")

        await interests.add(1, CITY_SLUG, "museums")
        await interests.add(1, CITY_SLUG, "walks")
        await interests.add(1, "another-city", "free")
        await interests.add(2, CITY_SLUG, "architecture")

        summary = await build_profile_summary(
            1,
            get_catalog(CITY_SLUG),
            favorites_repo=favorites,
            interests_repo=interests,
            visited_repo=visited,
        )

        assert summary.city_name == "Санкт-Петербург"
        assert summary.favorites_count == 1
        assert summary.visited_count == 1
        assert summary.interest_labels == (
            INTEREST_LABELS["museums"],
            INTEREST_LABELS["walks"],
        )

    asyncio.run(scenario())


def test_profile_summary_handles_empty_state(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)

        summary = await build_profile_summary(
            99,
            get_catalog(CITY_SLUG),
            favorites_repo=FavoritesRepository(database_path),
            interests_repo=InterestsRepository(database_path),
            visited_repo=VisitedRepository(database_path),
        )

        assert summary.interests_text == "не выбраны"
        assert summary.favorites_count == 0
        assert summary.visited_count == 0

        text = profile_text(summary)
        assert "Интересы: не выбраны" in text
        assert "Избранное: 0" in text
        assert "Посещённые: 0" in text

    asyncio.run(scenario())
