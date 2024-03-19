import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, MessageReactionUpdated

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.rating import is_rating_cached


class RatingCacheReactionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[MessageReactionUpdated, Dict[str, Any]], Awaitable[Any]],
        reaction: MessageReactionUpdated,
        data: Dict[str, Any],
    ) -> Any:
        ratings_cache = data["ratings_cache"]
        repo: RequestsRepo = data["repo"]

        user_id = reaction.user.id if reaction.user else reaction.actor_chat.id
        helper_id = (
            await repo.message_user.get_user_id_by_message_id(
                reaction.chat.id, reaction.message_id
            )
            or reaction.chat.id
        )
        cached = is_rating_cached(
            helper_id,
            user_id,
            ratings_cache,
        )
        if cached:
            logging.info("Cached rating reaction. Ignoring.")
            return

        data["helper_id"] = helper_id
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
