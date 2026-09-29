import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.catalog_context import CatalogMiddleware
from app.catalog_service import CatalogService
from app.config import get_settings
from app.database import migrate_database
from app.handlers.main import router
from app.user_data_controls import UserDataControlsRepository
from app.storage import (
    FavoritesRepository,
    InterestsRepository,
    SavedRoutesRepository,
    UserCityRepository,
    VisitedRepository,
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    await migrate_database(settings.database_path)
    favorites_repo = FavoritesRepository(settings.database_path)
    interests_repo = InterestsRepository(settings.database_path)
    visited_repo = VisitedRepository(settings.database_path)
    saved_routes_repo = SavedRoutesRepository(settings.database_path)
    user_city_repo = UserCityRepository(settings.database_path)
    data_controls_repo = UserDataControlsRepository(settings.database_path)
    catalog_service = CatalogService(
        default_city_slug=settings.city_slug,
        user_city_repo=user_city_repo,
    )

    bot = Bot(
        token=settings.require_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["favorites_repo"] = favorites_repo
    dispatcher["interests_repo"] = interests_repo
    dispatcher["visited_repo"] = visited_repo
    dispatcher["saved_routes_repo"] = saved_routes_repo
    dispatcher["data_controls_repo"] = data_controls_repo
    dispatcher["catalog_service"] = catalog_service
    dispatcher.update.outer_middleware(CatalogMiddleware(catalog_service))
    dispatcher.include_router(router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть городской гид"),
            BotCommand(command="city", description="Выбрать город"),
            BotCommand(command="profile", description="Открыть «Мой гид»"),
            BotCommand(command="export", description="Экспортировать мои данные"),
        ]
    )
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
