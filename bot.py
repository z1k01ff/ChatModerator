import asyncio
import logging

import betterlogging as bl
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from openai import AsyncOpenAI

from infrastructure.database.repo.requests import Database
from infrastructure.database.setup import create_engine, create_session_pool
from tgbot.config import load_config, Config
from tgbot.handlers.essential.fun import fun_router
from tgbot.handlers.groups import group_router
from tgbot.handlers.private.basic import basic_router
from tgbot.middlewares.config import ConfigMiddleware
from tgbot.middlewares.database import DatabaseMiddleware
from tgbot.middlewares.policy_content import OpenAIModerationMiddleware
from tgbot.middlewares.throttling import ThrottlingMiddleware
from tgbot.misc.default_commands import set_default_commands
from tgbot.services import broadcaster


async def on_startup(bot: Bot, admin_ids: list[int]):
    await broadcaster.broadcast(bot, admin_ids, "Бот був запущений")
    await set_default_commands(bot)


def register_global_middlewares(dp: Dispatcher, config: Config, session_pool,
                                openai_client):
    """
    Register global middlewares for the given dispatcher.
    Global middlewares here are the ones that are applied to all the handlers (you specify the type of update)

    :param dp: The dispatcher instance.
    :type dp: Dispatcher
    :param config: The configuration object from the loaded configuration.
    :param session_pool: Optional session pool object for the database using SQLAlchemy.
    :return: None
    """
    middleware_types = [
        ConfigMiddleware(config),
        OpenAIModerationMiddleware(openai_client),
    ]

    for middleware_type in middleware_types:
        dp.message.outer_middleware(middleware_type)
        dp.callback_query.outer_middleware(middleware_type)
    dp.message.middleware(ThrottlingMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware(session_pool))


def setup_logging():
    """
    Set up logging configuration for the application.

    This method initializes the logging configuration for the application.
    It sets the log level to INFO and configures a basic colorized log for
    output. The log format includes the filename, line number, log level,
    timestamp, logger name, and log message.

    Returns:
        None

    Example usage:
        setup_logging()
    """
    log_level = logging.INFO
    bl.basic_colorized_config(level=log_level)

    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot")


def get_storage(config):
    """
    Return storage based on the provided configuration.

    Args:
        config (Config): The configuration object.

    Returns:
        Storage: The storage object based on the configuration.

    """
    if config.tg_bot.use_redis:
        return RedisStorage.from_url(
            config.redis.dsn(),
            key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        )
    else:
        return MemoryStorage()


async def main():
    setup_logging()

    config = load_config(".env")
    storage = get_storage(config)

    bot = Bot(token=config.tg_bot.token, parse_mode="HTML")
    dp = Dispatcher(storage=storage)
    engine = create_engine("main.db")
    db = Database(engine)
    await db.create_tables()
    session_pool = create_session_pool(engine)
    ratings_cache = {}
    openai_client = AsyncOpenAI(api_key=config.openai.api_key)

    dp.include_routers(
        group_router,
        fun_router,
        basic_router,
    )

    register_global_middlewares(dp, config, session_pool, openai_client)

    await on_startup(bot, config.tg_bot.admin_ids)
    dp.workflow_data.update(
        ratings_cache=ratings_cache,
    )
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Бот був вимкнений!")
