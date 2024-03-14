from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.repo.requests import RequestsRepo


class RatingFilter(BaseFilter):
    def __init__(self, rating: int):
        self.rating = rating

    async def __call__(self, obj: Message, repo: RequestsRepo) -> bool:
        user_id = obj.from_user.id
        user_rating = await repo.rating_users.get_rating_by_user_id(user_id)
        if not user_rating:
            return False

        if user_rating > self.rating:
            return True
        else:
            rating_left = self.rating - user_rating
            await obj.answer(
                f"Вам не вистачає {rating_left} рейтингу для виконання цієї дії"
            )
