import typing
from dataclasses import dataclass

from aiogram import types
from aiogram.enums import ChatMemberStatus
from aiogram.filters import BaseFilter
from aiogram.types import ChatMemberAdministrator


@dataclass
class HasPermissionsFilter(BaseFilter):
    can_post_messages: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    can_restrict_members: bool = False
    can_promote_members: bool = False
    can_change_info: bool = False
    can_invite_users: bool = False
    can_pin_messages: bool = False
    CHAT_ADMINS: typing.ClassVar[typing.Dict[int, typing.List[types.ChatMember]]] = {}

    async def __call__(self, message: types.Message) -> bool | dict | None:
        chat_id = message.chat.id
        user_id = message.from_user.id

        if chat_id not in self.CHAT_ADMINS:
            self.CHAT_ADMINS[chat_id] = await message.chat.get_administrators()

        chat_member: ChatMemberAdministrator = next(
            (
                member
                for member in self.CHAT_ADMINS[chat_id]
                if member.user.id == user_id
            ),
            None,
        )

        if not chat_member:
            return False  # User not found among chat admins

        # Handle the case where the user is the chat creator
        if chat_member.status == ChatMemberStatus.CREATOR:
            return {"is_admin": True}

        checks = [
            (self.can_delete_messages, chat_member.can_delete_messages),
            (self.can_restrict_members, chat_member.can_restrict_members),
        ]

        if all(required == granted for required, granted in checks if required):
            return {"is_admin": True}
