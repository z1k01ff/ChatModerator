import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message, MessageReactionUpdated, Chat

from tgbot.misc.time_utils import format_time

from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage

THROTTLING_STORAGE_KEY = "throttling"


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self.users: dict
        self.storage: RedisStorage

    async def get_users_from_storage(self, data: dict):
        self.storage = data.get("state").storage
        bot: Bot = data.get("bot")
        event_chat: Chat = data.get("event_chat")
        chat_data: dict = await self.storage.get_data(
            StorageKey(
                bot_id=bot.id,
                chat_id=event_chat.id,
                user_id=event_chat.id,
            )
        )

        throttling_data = chat_data.get(THROTTLING_STORAGE_KEY, {})
        self.users = {
            key: (datetime.fromisoformat(time_str), count)
            for key, (time_str, count) in throttling_data.items()
        }

    async def set_users_to_storage(self, data: dict):
        bot: Bot = data.get("bot")
        event_chat: Chat = data.get("event_chat")
        throttling_data = {
            key: (time_obj.isoformat(), count)
            for key, (time_obj, count) in self.users.items()
        }

        await self.storage.update_data(
            StorageKey(
                bot_id=bot.id,
                chat_id=event_chat.id,
                user_id=event_chat.id,
            ),
            {THROTTLING_STORAGE_KEY: throttling_data},
        )

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, MessageReactionUpdated], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, MessageReactionUpdated],
        data: Dict[str, Any],
    ) -> Any:
        event_from_user = data.get("event_from_user")
        if not event_from_user:
            return await handler(event, data)
        user_id = event_from_user.id

        now = datetime.now()
        rate_limit = get_flag(data, "rate_limit")
        if not rate_limit:
            logging.info(f"No rate limit found: {rate_limit}")
            return await handler(event, data)

        if self._is_override(data, user_id):
            return await handler(event, data)

        key_prefix = rate_limit.get("key", "antiflood")
        limit = rate_limit.get("limit", 30)
        max_times = rate_limit.get("max_times", 1)
        chat_marker = data.get("chat")
        silent = rate_limit.get("silent", False)

        if chat_marker is not None:
            key = f"{key_prefix}:{event.chat.id}"
        else:
            key = f"{key_prefix}:{user_id}"

        await self.get_users_from_storage(data)
        if left_time := self._should_throttle(key, now, limit, max_times):
            await self.set_users_to_storage(data)
            logging.info(f"Throttling {user_id} for {key_prefix}")
            if isinstance(event, Message):
                if not silent:
                    notification = await event.answer(
                        f"Занадто часто! Повторіть спробу через {format_time(left_time)}."
                    )

                    await asyncio.sleep(5)
                    await notification.delete()
                    if isinstance(event, Message):
                        await event.delete()
            return  # Stop processing if throttled

        await self.set_users_to_storage(data)
        # Proceed with the next handler if not throttled
        return await handler(event, data)

    def _is_override(self, data, user_id):
        override = get_flag(data, "override")
        logging.info(f"Override: {override}")
        if override:
            user_override = override.get("user_id")
            return user_override == user_id
        return False

    def _should_throttle(self, key, now, limit, max_times):
        if key in self.users:
            last_time, throttle_count = self.users[key]
            if now - last_time < timedelta(seconds=limit):
                if throttle_count < max_times:
                    # Increment the throttle count and return False (don't throttle yet)
                    self.users[key] = (now, throttle_count + 1)
                    return False
                else:
                    # Throttle if max_times is reached
                    return limit - (now - self.users[key][0]).seconds
        # Not previously throttled or time limit passed, reset or initialize throttle data
        self.users[key] = (now, 1)  # Start counting throttling attempts
        return False
