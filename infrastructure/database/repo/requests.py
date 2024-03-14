import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Base
from infrastructure.database.models.tables import (
    BannedStickers,
    ChatAdmins,
    MessageUser,
    RatingUsers,
)


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


class ChatAdminsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def select_all_chat_admins(self, chat_id: int) -> List[ChatAdmins]:
        stmt = select(ChatAdmins.admin_id).where(ChatAdmins.chat_id == chat_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_chat_admin(self, chat_id: int, admin_id: int):
        stmt = insert(ChatAdmins).values(chat_id=chat_id, admin_id=admin_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def del_chat_admin(self, chat_id: int, admin_id: int):
        stmt = delete(ChatAdmins).where(
            ChatAdmins.chat_id == chat_id, ChatAdmins.admin_id == admin_id
        )
        await self.session.execute(stmt)
        await self.session.commit()


class RatingUsersRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_user_for_rating(self, user_id: int, rating: int):
        stmt = insert(RatingUsers).values(user_id=user_id, rating=rating)
        await self.session.execute(stmt)
        await self.session.commit()

    async def increment_rating_by_user_id(self, user_id: int, increment: int):
        stmt = (
            update(RatingUsers)
            .where(RatingUsers.user_id == user_id)
            .values(rating=RatingUsers.rating + increment)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_rating_by_user_id(self, user_id: int) -> Optional[int]:
        stmt = select(RatingUsers.rating).where(RatingUsers.user_id == user_id)
        result = await self.session.execute(stmt)
        rating = result.scalar()
        logging.info(f"Rating for user {user_id}: {rating}")
        return rating

    async def update_rating_by_user_id(self, user_id: int, rating: int):
        stmt = (
            update(RatingUsers)
            .where(RatingUsers.user_id == user_id)
            .values(rating=rating)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_top_by_rating(self, limit=10) -> List[RatingUsers]:
        stmt = (
            select(RatingUsers.user_id, RatingUsers.rating)
            .order_by(RatingUsers.rating.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.all()


class MessageUserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    # add message to the database
    # get user_id by message_id and chat_id
    async def add_message(self, user_id: int, chat_id: int, message_id: int):
        stmt = insert(MessageUser).values(
            user_id=user_id, chat_id=chat_id, message_id=message_id
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_user_id_by_message_id(
        self, chat_id: int, message_id: int
    ) -> Optional[int]:
        stmt = select(MessageUser.user_id).where(
            MessageUser.chat_id == chat_id, MessageUser.message_id == message_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


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
    def chat_admins(self) -> ChatAdminsRepo:
        return ChatAdminsRepo(self.session)

    @property
    def rating_users(self) -> RatingUsersRepo:
        return RatingUsersRepo(self.session)

    @property
    def message_user(self) -> MessageUserRepo:
        return MessageUserRepo(self.session)


class Database:
    def __init__(self, engine):
        self.engine = engine

    async def create_tables(self):
        # Async function to create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
