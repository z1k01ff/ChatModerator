from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select, insert, delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Base
from infrastructure.database.models.tables import BannedStickers, ChatAdmins, RatingUsers


class BannedStickersRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def block_sticker(self, set_name: str):
        stmt = insert(BannedStickers).values(set_name=set_name)
        await self.session.execute(stmt)
        await self.session.commit()

    async def select_all_sets(self) -> List[BannedStickers]:
        stmt = select(BannedStickers)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class RatingUsersRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_user_for_rating(self, user_id: int, rating: int):
        stmt = insert(RatingUsers).values(user_id=user_id, rating=rating)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_rating_by_user_id(self, user_id: int) -> Optional[RatingUsers]:
        stmt = select(RatingUsers.rating).where(RatingUsers.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_rating_by_user_id(self, user_id: int, rating: int):
        stmt = update(RatingUsers).where(RatingUsers.user_id == user_id).values(
            rating=rating)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_top_by_rating(self, limit=10) -> List[RatingUsers]:
        stmt = select(RatingUsers.user_id, RatingUsers.rating).order_by(RatingUsers.rating.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.all()


@dataclass
class RequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def banned_stickers(self) -> BannedStickersRepo:
        return BannedStickersRepo(self.session)


    @property
    def rating_users(self) -> RatingUsersRepo:
        return RatingUsersRepo(self.session)


class Database:
    def __init__(self, engine):
        self.engine = engine

    async def create_tables(self):
        # Async function to create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)