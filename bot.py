import asyncio
import random
from elevenlabs.client import AsyncElevenLabs
import logging

import betterlogging as bl
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from anthropic import AsyncAnthropic
import httpx
from openai import AsyncOpenAI
from pyrogram import Client

from infrastructure.database.setup import create_engine, create_session_pool
from tgbot.config import Config, load_config
from tgbot.handlers.essential.fun import fun_router
from tgbot.handlers.groups import (
    ai_router,
    group_router,
    groups_rating_router,
    payment_router,
)
from tgbot.handlers.private.basic import basic_router
from tgbot.handlers.private.admin import admin_router
from tgbot.middlewares.bot_messages import BotMessages
from tgbot.middlewares.database import DatabaseMiddleware
from tgbot.middlewares.policy_content import OpenAIModerationMiddleware
from tgbot.middlewares.ratings_cache import (
    MessageUserMiddleware,
)
from tgbot.middlewares.throttling import ThrottlingMiddleware
from tgbot.misc.default_commands import set_default_commands
from tgbot.services import broadcaster
from tgbot.misc.phrases import bot_startup_phrases
from aiogram.client.default import DefaultBotProperties


async def on_startup(bot: Bot, config: Config, client: Client) -> None:
    admin_ids = config.tg_bot.admin_ids
    await broadcaster.broadcast(bot, admin_ids, random.choice(bot_startup_phrases))
    await set_default_commands(bot)
    await client.start()


async def shutdown(client: Client) -> None:
    await client.stop()


def register_global_middlewares(
    dp: Dispatcher,
    config: Config,
    session_pool,
    openai_client,
    storage,
):
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
        OpenAIModerationMiddleware(openai_client),
    ]

    for middleware_type in middleware_types:
        dp.message.outer_middleware(middleware_type)
        dp.callback_query.outer_middleware(middleware_type)
    dp.message.middleware(ThrottlingMiddleware(storage))
    dp.message_reaction.middleware(ThrottlingMiddleware(storage))
    dp.update.outer_middleware(DatabaseMiddleware(session_pool))
    dp.message.outer_middleware(MessageUserMiddleware())


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

    bot = Bot(
        token=config.tg_bot.token, default=DefaultBotProperties(parse_mode="HTML")
    )
    engine = create_engine(config.db.construct_sqlalchemy_url())
    client = Client(
        name="bot",
        bot_token=config.tg_bot.token,
        api_id=config.client.api_id,
        api_hash=config.client.api_hash,
        no_updates=True,  # We don't need to handle incoming updates by client
    )
    dp = Dispatcher(storage=storage, client=client, fsm_strategy=FSMStrategy.CHAT)
    session_pool = create_session_pool(engine)
    ratings_cache = {}
    openai_client = AsyncOpenAI(api_key=config.openai.api_key)

    elevenlabs_client = AsyncElevenLabs(
        api_key=config.elevenlabs.api_key,
        httpx_client=httpx.AsyncClient(),
    )

    anthropic_client = AsyncAnthropic(
        api_key=config.anthropic.api_key,
    )

    dp.include_routers(
        payment_router,
        groups_rating_router,
        group_router,
        fun_router,
        basic_router,
        admin_router,
        ai_router,
    )

    register_global_middlewares(dp, config, session_pool, openai_client, storage)

    dp.workflow_data.update(
        ratings_cache=ratings_cache,
        anthropic_client=anthropic_client,
        openai_client=openai_client,
        elevenlabs_client=elevenlabs_client,
    )
    bot.session.middleware(BotMessages(session_pool))
    await bot.delete_webhook()
    dp.startup.register(on_startup)
    dp.shutdown.register(shutdown)
    await dp.start_polling(bot, config=config)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Бот був вимкнений!")
