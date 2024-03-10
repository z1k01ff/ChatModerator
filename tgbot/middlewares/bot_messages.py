import logging
from typing import TYPE_CHECKING

from aiogram import types
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.methods import SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from infrastructure.database.repo.requests import RequestsRepo

if TYPE_CHECKING:
    from ...bot import Bot

logger = logging.getLogger(__name__)


class BotMessages(BaseRequestMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: "Bot",
        method: TelegramMethod[TelegramType],
    ):
        if method.__class__.__name__ == SendMessage.__name__:
            async with self.session_pool() as session:
                repo = RequestsRepo(session)
                result: types.Message = await make_request(bot, method)
                await repo.message_user.add_message(
                    user_id=827638584,
                    chat_id=result.chat.id,
                    message_id=result.message_id,
                )
                logging.info(
                    f"Bot's message added to the database with {result.message_id}"
                )

                return result

        return await make_request(bot, method)
