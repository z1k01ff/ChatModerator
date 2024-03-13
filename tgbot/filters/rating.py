from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.repo.requests import RequestsRepo


class RatingFilter(BaseFilter):
    def __init__(self, rating: int):
        self.rating = rating

    async def __call__(self, obj: Message, repo: RequestsRepo) -> bool:
        user_id = obj.from_user.id
        user_rating = await repo.rating_users.get_rating_by_user_id(user_id)
        return user_rating is not None and user_rating > self.rating
