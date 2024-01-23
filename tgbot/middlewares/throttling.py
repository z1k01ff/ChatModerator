import logging
from re import U
from typing import Callable, Dict, Any, Awaitable, Union
import asyncio
from datetime import datetime, timedelta

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
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, MessageReactionUpdated):
            user_id = event.user.id
        else:
            return await handler(event, data)

        now = datetime.now()

        rate_limit = get_flag(data, "rate_limit")
        override = get_flag(data, "override")
        if not rate_limit:
            return await handler(event, data)

        if override:
            user_override = override.get("user_id")
            if user_override == user_id:
                return await handler(event, data)

        key_prefix = rate_limit.get("key", "antiflood")
        limit = rate_limit.get("limit", 30)
        logging.info(f"key_prefix: {key_prefix}, limit: {limit}")

        key = f"{key_prefix}:{user_id}"
        if key in self.users:
            last_time, throttle_count = self.users[key]
            if now - last_time < timedelta(seconds=limit):
                if throttle_count == 0:
                    if isinstance(event, Message):
                        await event.answer("Занадто часто!")
                    self.users[key] = (now, throttle_count + 1)
                    return
                # Increase the throttle count instead of resetting it
                self.users[key] = (now, throttle_count + 1)
            else:
                # Reset throttle count only if time limit has passed
                self.users[key] = (now, 0)
        else:
            self.users[key] = (now, 0)

        # Call the next handler
        return await handler(event, data)
