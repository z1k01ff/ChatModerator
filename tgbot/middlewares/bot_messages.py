import logging

from aiogram import Bot, types
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.methods import SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from infrastructure.database.repo.requests import RequestsRepo

logger = logging.getLogger(__name__)


class BotMessages(BaseRequestMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ):
        if isinstance(method, SendMessage):
            result: types.Message = await make_request(bot, method)
            async with self.session_pool() as session:
                repo = RequestsRepo(session)
                await repo.message_user.add_message(
                    user_id=result.from_user.id,
                    chat_id=result.chat.id,
                    message_id=result.message_id,
                )
                logging.info(
                    f"Bot's message added to the database with {result.message_id}"
                )

                return result

        return await make_request(bot, method)
