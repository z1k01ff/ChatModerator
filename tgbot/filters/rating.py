from aiogram.filters import BaseFilter
from aiogram.types import Message, User

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.broadcaster import send_telegram_action


class RatingFilter(BaseFilter):
    def __init__(self, rating: int):
        self.rating = rating

    async def __call__(
        self, obj: Message, repo: RequestsRepo, event_from_user: User
    ) -> bool | dict:  # type: ignore
        user_rating = await repo.rating_users.get_rating_by_user_id(
            event_from_user.id, chat_id=obj.chat.id
        )
        if not user_rating:
            return False

        if user_rating >= self.rating:
            return {"rating": user_rating}
        else:
            if not isinstance(obj, Message):
                return False

            rating_left = self.rating - user_rating
            # await obj.reply(
            # f"Вам не вистачає {rating_left} рейтингу для виконання цієї дії"
            # )
            await send_telegram_action(
                obj.bot.send_message,
                chat_id=obj.chat.id,
                text=f"Вам не вистачає {rating_left} рейтингу для виконання цієї дії",
                reply_to_message_id=obj.message_id,
            )
            return False
