import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import get_settings
from app.handlers.main import router
from app.storage import FavoritesRepository, InterestsRepository


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

    favorites_repo = FavoritesRepository(settings.database_path)
    interests_repo = InterestsRepository(settings.database_path)
    await favorites_repo.initialize()
    await interests_repo.initialize()

    bot = Bot(
        token=settings.require_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["favorites_repo"] = favorites_repo
    dispatcher["interests_repo"] = interests_repo
    dispatcher.include_router(router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть городской гид"),
        ]
    )
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
