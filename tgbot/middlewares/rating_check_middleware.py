from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message

from tgbot.services.broadcaster import send_telegram_action

class RatingCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        rating_left = data.get("rating_left")
        
        if rating_left is not None:
            await send_telegram_action(
                event.bot.send_message,
                chat_id=event.chat.id,
                text=f"Вам не вистачає {rating_left} рейтингу для виконання цієї дії",
                reply_to_message_id=event.message_id,
            )
            return None  # Discard the update
        
        return await handler(event, data)