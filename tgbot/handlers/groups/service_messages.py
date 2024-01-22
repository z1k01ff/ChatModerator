from aiogram import types, Router
from aiogram.enums import ChatMemberStatus

from infrastructure.database.repo.requests import RequestsRepo

service_message_router = Router()

@service_message_router.chat_member()
async def updated_chat_member(chat_member_updated: types.ChatMemberUpdated,
                              repo: RequestsRepo):
    """Хендлер для вышедших либо кикнутых пользователей"""

    performer_mention = chat_member_updated.from_user.mention_html()
    member_mention = chat_member_updated.old_chat_member.user.mention_html()

    bot_user = await chat_member_updated.bot.me()
    if chat_member_updated.from_user.id == bot_user.id:
        return False

    if chat_member_updated.new_chat_member.status == ChatMemberStatus.MEMBER:
        # REMOVED. Now bot approves users on join request in private chat
        pass
    if chat_member_updated.new_chat_member.status == ChatMemberStatus.KICKED:
        text = f"{member_mention} был удален из чата пользователем {performer_mention}."

    elif chat_member_updated.new_chat_member.status == ChatMemberStatus.RESTRICTED \
            and chat_member_updated.old_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        text = f"Для пользователя {member_mention} были изменены права пользователем {performer_mention}."


    elif chat_member_updated.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        if chat_member_updated.old_chat_member.status != ChatMemberStatus.ADMINISTRATOR:
            await repo.chat_admins.add_chat_admin(chat_member_updated.chat.id,
                                                  chat_member_updated.from_user.id)
            text = f'Пользователь {member_mention} был повышен до статуса Администратора чата с титулом: ' \
                   f'{chat_member_updated.new_chat_member.custom_title or "Без титула"}.'
        else:
            text = f'Для администратора {member_mention} были изменены права'

    elif (chat_member_updated.old_chat_member.status == ChatMemberStatus.ADMINISTRATOR
          and chat_member_updated.new_chat_member.status != ChatMemberStatus.ADMINISTRATOR):
        await repo.chat_admins.del_chat_admin(chat_member_updated.chat.id,
                                              chat_member_updated.from_user.id)
        text = f'Администратора {member_mention} понизили до статуса Пользователь'
    else:
        return

    await chat_member_updated.bot.send_message(
        chat_member_updated.chat.id,
        text
    )
