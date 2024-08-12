from sqlalchemy import BIGINT, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class BannedStickers(Base):
    __tablename__ = "BannedStickers"
    set_name: Mapped[str] = mapped_column(String(255), primary_key=True)

    def __repr__(self):
        return f"<BannedStickers {self.set_name}>"


class ChatAdmins(Base):
    __tablename__ = "ChatAdmins"
    """
    Represents chat administrators in the application.
    """
    chat_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)

    def __repr__(self):
        return f"<ChatAdmins chat_id={self.chat_id} admin_id={self.admin_id}>"


class RatingUsers(Base):
    __tablename__ = "RatingUsers"
    """
    Represents user ratings in the application.
    """
    user_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    chat_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    rating: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self):
        return f"<RatingUsers user_id={self.user_id} chat_id={self.chat_id} rating={self.rating}>"


class MessageUser(Base, TableNameMixin):
    user_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    chat_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    message_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )