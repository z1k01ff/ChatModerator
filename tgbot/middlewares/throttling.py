import asyncio
from contextlib import suppress
import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message, MessageReactionUpdated

from tgbot.misc.time_utils import format_time

from aiogram.fsm.storage.redis import RedisStorage

from tgbot.services.broadcaster import send_telegram_action
from tgbot.services.token_usage import Sonnet, TokenUsageManager


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, storage: RedisStorage, bot: Bot) -> None:
        super().__init__()
        self.storage: RedisStorage = storage
        self.ai_token_usage = TokenUsageManager(storage=storage,bot=bot)

    async def _get_throttle_count(self, key: str) -> int:
        count = await self.storage.redis.get(key)
        return int(count) if count is not None else 0

    async def _set_throttle_count(self, key: str, count: int, ttl: int) -> None:
        await self.storage.redis.set(key, count, ex=ttl)

    async def _get_remaining_ttl(self, key: str) -> int:
        ttl = await self.storage.redis.ttl(key)
        return int(ttl) if ttl > 0 else 0  # Ensure ttl is non-negative

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

        rate_limit = get_flag(data, "rate_limit")
        if not rate_limit:
            logging.info(f"No rate limit found: {rate_limit}")
            return await handler(event, data)

        if self._is_override(data, user_id):
            return await handler(event, data)

        # Check for AI-related flag
        is_ai_interaction = get_flag(data, "is_ai_interaction")

        key_prefix = rate_limit.get("key", "antiflood")
        limit = rate_limit.get("limit", 30)
        max_times = rate_limit.get("max_times", 1)
        chat_marker = rate_limit.get("chat")
        silent = rate_limit.get("silent", False)

        key = f"THROTTLING:{key_prefix}:{event.chat.id if chat_marker else user_id}"
        current_count = await self._get_throttle_count(key)
        logging.info(f"Current count: {current_count}")
        logging.info(f"Max times: {max_times}")
    
        # Handle AI interactions
        if is_ai_interaction is not None:
            usage_cost = await self.ai_token_usage.calculate_cost(Sonnet, event.chat.id, user_id)
            if usage_cost <= 2:
                logging.info("User is free from rate limit (ai_interaction)")
                # No rate limit for AI interactions that don't require payment
                return await handler(event, data)
            elif event.quote:
                return
            else:
                # Strict rate limit for AI interactions that require payment
                logging.info("User has to pay for AI interaction, set limit to 1x5mins")
                limit = 600  # 10 minutes
                max_times = 1
                data["user_needs_to_pay"] = True

        if current_count >= max_times:
            remaining_ttl = await self._get_remaining_ttl(key)
            logging.info(f"Throttling {user_id} for {key_prefix}")
            if isinstance(event, Message) and not silent:
                bot = data.get("bot")
                notification = await send_telegram_action(
                    bot.send_message,
                    chat_id=event.chat.id,
                    text=f"Занадто часто! Повторіть спробу через {format_time(remaining_ttl)}.",
                    reply_to_message_id=event.message_id,
                )
                await asyncio.sleep(5)
                with suppress(Exception):
                    await event.delete()
                    await notification.delete()
            return  # Stop processing if throttled

        # Increment or initialize the throttle count
        await self._set_throttle_count(key, current_count + 1, int(limit))

        # Proceed with the next handler if not throttled
        return await handler(event, data)

    def _is_override(self, data, user_id):
        override = get_flag(data, "override")
        logging.info(f"Override: {override}")
        if override:
            user_override = override.get("user_id")
            return user_override == user_id
        return False
