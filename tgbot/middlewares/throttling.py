import logging
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message, MessageReactionUpdated


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self.users = {}

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

        if self._is_override(handler, user_id):
            return await handler(event, data)

        key_prefix = rate_limit.get("key", "antiflood")
        limit = rate_limit.get("limit", 30)
        key = f"{key_prefix}:{user_id}"
        max_times = rate_limit.get("max_times", 1)

        if self._should_throttle(key, now, limit, max_times):
            logging.info(f"Throttling {user_id} for {key_prefix}")
            if isinstance(event, Message):
                await event.answer("Занадто часто!")
            return  # Stop processing if throttled

        # Proceed with the next handler if not throttled
        return await handler(event, data)

    def _is_override(self, handler, user_id):
        # override = self._get_flag(data, "override")
        override = get_flag(handler, "override")
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
                    return True
        # Not previously throttled or time limit passed, reset or initialize throttle data
        self.users[key] = (now, 1)  # Start counting throttling attempts
        return False
