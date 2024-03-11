import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message, MessageReactionUpdated

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.rating import is_rating_cached


class RatingCacheMessageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        m: Message,
        data: Dict[str, Any],
    ) -> Any:
        ratings_cache = data["ratings_cache"]

        rating_cache_flag = get_flag(data, "rating_cache")
        if not rating_cache_flag:
            return await handler(m, data)

        user_id = m.from_user.id  # айди юзера, который поставил + или -
        message_id = m.reply_to_message.message_id

        cached = is_rating_cached(m.chat.id, user_id, message_id, ratings_cache)
        if cached:
            await m.delete()
            return

        return await handler(m, data)


class RatingCacheReactionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[MessageReactionUpdated, Dict[str, Any]], Awaitable[Any]],
        reaction: MessageReactionUpdated,
        data: Dict[str, Any],
    ) -> Any:
        ratings_cache = data["ratings_cache"]

        user_id = reaction.user.id if reaction.user else reaction.actor_chat.id

        cached = is_rating_cached(reaction.chat.id, user_id, ratings_cache)
        if cached:
            logging.info("Cached rating reaction. Ignoring.")
            return

        return await handler(reaction, data)


class MessageUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        m: Message,
        data: Dict[str, Any],
    ) -> Any:
        repo: RequestsRepo = data["repo"]

        await repo.message_user.add_message(m.from_user.id, m.chat.id, m.message_id)
        return await handler(m, data)
