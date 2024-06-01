from aiogram import types, Router
from aiogram.enums import ChatMemberStatus
from infrastructure.database.repo.requests import RequestsRepo

service_message_router = Router()

@service_message_router.chat_member()
async def updated_chat_member(chat_member_updated: types.ChatMemberUpdated, repo: RequestsRepo):
    """Хендлер для нових або виключених користувачів"""

    performer_mention = chat_member_updated.from_user.mention_html()
    member_mention = chat_member_updated.old_chat_member.user.mention_html()

    bot_user = await chat_member_updated.bot.me()
    if chat_member_updated.from_user.id == bot_user.id:
        return

    if chat_member_updated.new_chat_member.status == ChatMemberStatus.MEMBER:
        # Встановити рейтинг 5 для нового користувача
        new_member_id = chat_member_updated.new_chat_member.user.id
        await repo.update_rating_by_user_id(new_member_id, 5)
        text = f"{member_mention} був доданий до чату користувачем {performer_mention} і отримав рейтинг 5."
        # Привітати нового користувача
        greeting_text = f"Ласкаво просимо до чату, {member_mention}! Ваш початковий рейтинг встановлено на 5."
        await chat_member_updated.bot.send_message(chat_member_updated.chat.id, greeting_text)
    elif chat_member_updated.new_chat_member.status == ChatMemberStatus.KICKED:
        text = f"{member_mention} був видалений з чату користувачем {performer_mention}."
    elif (
        chat_member_updated.new_chat_member.status == ChatMemberStatus.RESTRICTED
        and chat_member_updated.old_chat_member.status == ChatMemberStatus.ADMINISTRATOR
    ):
        text = f"{performer_mention} змінив права для користувача {member_mention}."
    elif chat_member_updated.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        if chat_member_updated.old_chat_member.status != ChatMemberStatus.ADMINISTRATOR:
            await repo.chat_admins.add_chat_admin(chat_member_updated.chat.id, chat_member_updated.from_user.id)
            text = (
                f"{performer_mention} підвищив {member_mention} до статусу адміністратора чату "
                f"з титулом: {chat_member_updated.new_chat_member.custom_title or 'Без титулу'}."
            )
        else:
            text = f"{performer_mention} змінив права для адміністратора {member_mention}."
    elif (
        chat_member_updated.old_chat_member.status == ChatMemberStatus.ADMINISTRATOR
        and chat_member_updated.new_chat_member.status != ChatMemberStatus.ADMINISTRATOR
    ):
        new_status = {
            ChatMemberStatus.RESTRICTED: "Обмежений",
            ChatMemberStatus.MEMBER: "Користувач",
            ChatMemberStatus.KICKED: "Виключений",
            ChatMemberStatus.LEFT: "Вийшов",
        }.get(chat_member_updated.new_chat_member.status, "Користувач")

        await repo.chat_admins.del_chat_admin(chat_member_updated.chat.id, chat_member_updated.from_user.id)
        text = f"{performer_mention} понизив {member_mention} до статусу {new_status}."
    else:
        return

    await chat_member_updated.bot.send_message(chat_member_updated.chat.id, text)