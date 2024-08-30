from dataclasses import dataclass

from aiogram import types
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import BaseFilter

ChatMemberType = (
    types.ChatMemberOwner
    | types.ChatMemberAdministrator
    | types.ChatMemberMember
    | types.ChatMemberRestricted
    | types.ChatMemberLeft
    | types.ChatMemberBanned
)


async def get_chat_member_status(
    chat_admins: dict[int, ChatMemberType], user_id: int
) -> ChatMemberType | None: 
    user= chat_admins.get(int(user_id))
    return user


async def is_user_admin(chat_admins: dict[int, ChatMemberType], user_id: int) -> bool:
    chat_member = await get_chat_member_status(chat_admins, user_id)
    return chat_member is not None and (
        chat_member.status == ChatMemberStatus.CREATOR
        or chat_member.status == ChatMemberStatus.ADMINISTRATOR
    )


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

    async def __call__(
        self, message: types.Message, chat_admins: dict[int, ChatMemberType]
    ) -> bool | dict | None:
        if message.chat.type == ChatType.PRIVATE:
            return False

        chat_member = await get_chat_member_status(chat_admins, message.from_user.id)

        if not chat_member:
            return False  # User not found among chat admins

        # Handle the case where the user is the chat creator
        if chat_member.status == ChatMemberStatus.CREATOR:
            return {"is_admin": True}

        if isinstance(chat_member, types.ChatMemberAdministrator):
            checks = [
                (self.can_delete_messages, chat_member.can_delete_messages),
                (self.can_restrict_members, chat_member.can_restrict_members),
                # Add other permission checks here
            ]

        if all(required == granted for required, granted in checks if required):
            return {"is_admin": True}

        return False
