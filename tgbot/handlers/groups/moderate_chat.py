import asyncio
import datetime
import logging
import re

from aiogram import Bot, F, Router, types
from aiogram.filters import Command

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.permissions import HasPermissionsFilter
from tgbot.filters.rating import RatingFilter
from tgbot.misc.permissions import (
    set_new_user_approved_permissions,
    set_no_media_permissions,
    set_user_ro_permissions,
)

restriction_time_regex = re.compile(r"(\b[1-9][0-9]*)([mhds]\b)")

groups_moderate_router = Router()


def get_members_info(message: types.Message):
    # Создаем переменные для удобства
    return [
        message.from_user.username,
        message.from_user.mention_html(),
        message.chat.id,
        message.reply_to_message.from_user.id,
        message.reply_to_message.from_user.username,
        message.reply_to_message.from_user.mention_html(),
    ]


def get_restriction_period(text: str) -> int:
    """
    Extract restriction period (in seconds) from text using regex search
    :param text: text to parse
    :return: restriction period in seconds (0 if nothing found, which means permanent restriction)
    """
    if match := re.search(restriction_time_regex, text):
        time, modifier = match.groups()
        multipliers = {"m": 60, "h": 3600, "d": 86400, "s": 1}
        return int(time) * multipliers[modifier]
    return 0


@groups_moderate_router.message(
    Command("ro", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
)
async def read_only_mode(message: types.Message, bot: Bot):
    """Хендлер с фильтром в группе, где можно использовать команду !ro ИЛИ /ro
    :time int: время на которое нужно замутить пользователя в минутах
    :reason str: причина мута. При отсутствии времени и/или причины, то
    используются стандартные значения: 5 минут и None для времени и причины соответственно

    Примеры:
    !ro 5m замутить пользователя на 5 минут
    """

    # Создаем переменные для удобства
    (
        admin_username,
        admin_mentioned,
        chat_id,
        member_id,
        member_username,
        member_mentioned,
    ) = get_members_info(message)

    # Разбиваем команду на аргументы с помощью RegExp

    # Revised regular expression to capture duration and reason
    command_parse = re.compile(r"(?:!ro|/ro)\s*(\d+[mhMH]?)?\s*(\S.*)")

    # Match the command against the input text
    parsed = command_parse.match(message.text)
    # Проверяем на наличие и корректность срока RO.
    # Проверяем на наличие причины.
    # reason = "без указания причины" if not reason else f"по причине: {reason}"

    if parsed:
        duration = parsed.group(1)  # This captures the duration
        reason = parsed.group(2)  # This captures the reason

        # Default values if not specified
        if not duration:
            duration = "5m"  # Default duration of 5 minutes if not specified
        if not reason:
            reason = "просто так"  # Default reason if not specified
        else:
            reason = f"в наслідок: {reason}"
        # Convert duration to seconds
        ro_period = get_restriction_period(
            duration
        )  # Implement this function based on your needs

        # Calculate the end date/time for the mute
        ro_end_date = message.date + datetime.timedelta(seconds=ro_period)
    else:
        ro_period = 300
        ro_end_date = message.date + datetime.timedelta(seconds=ro_period)
        reason = "просто так"

    try:
        # Пытаемся забрать права у пользователя
        await message.chat.restrict(
            user_id=member_id,
            permissions=set_user_ro_permissions(),
            until_date=ro_end_date,
        )

        # Отправляем сообщение
        await message.answer(
            f"Користувачу {member_mentioned} було заборонено писати до {ro_end_date.strftime('%d.%m.%Y %H:%M')} "
            f"адміністратором {admin_mentioned} {reason}"
        )

        # Вносим информацию о муте в лог
        logging.info(
            f"Пользователю @{member_username} запрещено писать сообщения до {ro_end_date.strftime('%d.%m.%Y %H:%M')} админом @{admin_username} "
        )

    # Если бот не может замутить пользователя (администратора), возникает ошибка BadRequest которую мы обрабатываем
    except Exception as e:
        logging.exception(e)
        chat_member = await message.chat.get_member(member_id)
        administrator = await message.chat.get_member(message.from_user.id)
        if chat_member.status == "administrator" or administrator.status == "creator":
            await message.chat.promote(
                user_id=member_id,
                is_anonymous=False,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_pin_messages=False,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_manage_topics=False,
            )
            await message.chat.restrict(
                user_id=member_id,
                permissions=set_user_ro_permissions(),
                until_date=ro_end_date,
            )

            await message.answer(
                f"Користувачу було заборонено писати до {ro_end_date.strftime('%d.%m.%Y %H:%M')} "
                f"адміністратором {admin_mentioned} {reason}. Також, користувач був понижений до рівня учасника"
            )

        # Отправляем сообщение
        await message.answer(
            f"Користувач {member_mentioned} є адміністратором чату, я не можу заборонити йому писати"
        )
        # Вносим информацию о муте в лог
        logging.info(f"Бот не смог замутить пользователя @{member_username}")
    service_message = await message.answer("Повідомлення самознищиться за 5 секунд.")

    await asyncio.sleep(5)
    # после прошедших 5 секунд, бот удаляет сообщение от администратора и от самого бота
    await message.delete()
    await service_message.delete()
    await message.reply_to_message.delete()


@groups_moderate_router.message(
    Command("unro", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
)
async def undo_read_only_mode(message: types.Message, bot: Bot):
    """Хендлер с фильтром в группе, где можно использовать команду !unro ИЛИ /unro"""
    (
        admin_username,
        admin_mentioned,
        chat_id,
        member_id,
        member_username,
        member_mentioned,
    ) = get_members_info(message)

    # Возвращаем пользователю возможность отправлять сообщения
    await bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=member_id,
        permissions=set_new_user_approved_permissions(),
    )

    # Информируем об этом
    await message.answer(
        # f"Пользователь {member_mentioned} был размучен администратором {admin_mentioned}"
        f"Користувач {member_mentioned} був розблокований адміністратором {admin_mentioned}"
    )
    # service_message = await message.reply("Сообщение самоуничтожится через 5 секунд.")
    service_message = await message.reply("Повідомлення самознищиться за 5 секунд.")

    # Не забываем про лог
    logging.info(
        f"Пользователь @{member_username} был размучен администратором @{admin_username}"
    )

    # Пауза 5 сек
    await asyncio.sleep(5)

    # Удаляем сообщения от бота и администратора
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(
    Command("ban", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
    F.reply_to_message.sender_chat,
)
async def ban_channel(message: types.Message):
    from_user = message.from_user
    sender_chat = message.reply_to_message.sender_chat

    admin_fullname = from_user.full_name
    admin_mentioned = from_user.mention_html()

    member_id = sender_chat.id
    member_fullname = sender_chat.title

    try:
        await message.chat.ban_sender_chat(member_id)

        await message.answer(
            # f"Канал {member_fullname} был успешно забанен администратором {admin_mentioned}\n"
            # f"Теперь владелец канала не сможет писать от имени любого из своих каналов"
            f"Канал {member_fullname} був заблокований адміністратором {admin_mentioned}\n"
            f"Тепер власник каналу не зможе писати від імені будь-якого зі своїх каналів"
        )

        logging.info(f"Канал {member_fullname} был забанен админом {admin_fullname}")
    except Exception:
        logging.info(f"Бот не смог забанить канал {member_fullname}")

    # service_message = await message.answer("Сообщение самоуничтожится через 5 секунд.")
    service_message = await message.answer("Повідомлення самознищиться за 5 секунд.")

    await asyncio.sleep(5)

    await message.reply_to_message.delete()
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(
    Command("ban", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
)
async def ban_user(message: types.Message):
    """Хендлер с фильтром в группе, где можно использовать команду !ban ИЛИ /ban"""

    # Создаем переменные для удобства
    admin_fullname = message.from_user.full_name
    admin_mentioned = message.from_user.mention_html()
    member_id = message.reply_to_message.from_user.id
    member_fullname = message.reply_to_message.from_user.full_name
    member_mentioned = message.reply_to_message.from_user.mention_html()
    try:
        # Пытаемся удалить пользователя из чата
        await message.chat.ban(user_id=member_id)
        # Информируем об этом
        await message.answer(
            f"Користувач {member_mentioned} був заблокований адміністратором {admin_mentioned}"
        )
        # Об успешном бане информируем разработчиков в лог
        logging.info(
            f"Пользователь {member_fullname} был забанен админом {admin_fullname}"
        )
    except Exception as e:
        # Отправляем сообщение
        logging.exception(e)
        await message.answer(
            f"Користувач {member_mentioned} є адміністратором чату, я не можу заблокувати його"
        )

        logging.info(f"Бот не смог забанить пользователя {member_fullname}")

    # service_message = await message.answer("Сообщение самоуничтожится через 5 секунд.")
    service_message = await message.answer("Повідомлення самознищиться за 5 секунд.")

    # После чего засыпаем на 5 секунд
    await asyncio.sleep(5)
    # Не забываем удалить сообщение, на которое ссылался администратор
    await message.reply_to_message.delete()
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(
    Command("unban", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
)
async def unban_channel(message: types.Message):
    from_user = message.from_user
    sender_chat = message.reply_to_message.sender_chat

    admin_username = from_user.username
    admin_mentioned = from_user.mention_html()

    member_id = sender_chat.id
    member_username = sender_chat.username
    member_mentioned = sender_chat

    try:
        await message.chat.unban_sender_chat(member_id)
    except Exception:
        return

    await message.answer(
        # f"Канал {member_mentioned} был разбанен администратором {admin_mentioned}\n"
        # f"Теперь владелец канала сможет писать от имени любого из своих каналов"
        f"Канал {member_mentioned} був розблокований адміністратором {admin_mentioned}\n"
        f"Тепер власник каналу зможе писати від імені будь-якого зі своїх каналів"
    )
    # service_message = await message.reply("Сообщение самоуничтожится через 5 секунд.")
    service_message = await message.reply("Повідомлення самознищиться за 5 секунд.")

    logging.info(f"Канал @{member_username} был забанен админом @{admin_username}")

    await asyncio.sleep(5)

    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(
    Command("unban", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
)
async def unban_user(message: types.Message):
    """Хендлер с фильтром в группе, где можно использовать команду !unban ИЛИ /unban"""

    # Создаем переменные для удобства
    admin_username = message.from_user.username
    admin_mentioned = message.from_user.mention_html()
    member_id = message.reply_to_message.from_user.id
    member_username = message.reply_to_message.from_user.username
    member_mentioned = message.reply_to_message.from_user.mention_html()

    # И разбаниваем
    await message.chat.unban(user_id=member_id)

    # Пишем в чат
    await message.answer(
        # f"Пользователь {member_mentioned} был разбанен администратором {admin_mentioned}"
        f"Користувач {member_mentioned} був розблокований адміністратором {admin_mentioned}"
    )
    # service_message = await message.reply("Сообщение самоуничтожится через 5 секунд.")
    service_message = await message.reply("Повідомлення самознищиться за 5 секунд.")

    # Пауза 5 сек
    await asyncio.sleep(5)

    # Записываем в логи
    logging.info(
        f"Пользователь @{member_username} был забанен админом @{admin_username}"
    )

    # Удаляем сообщения
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(
    Command("media_false", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
)
async def media_false_handler(message: types.Message):
    (
        admin_username,
        admin_mentioned,
        chat_id,
        member_id,
        member_username,
        member_mentioned,
    ) = get_members_info(message)

    command_parse = re.compile(r"(!media_false|/media_false) ?(\d+)?")
    parsed = command_parse.match(message.text)
    time = parsed.group(2)

    answer_text = f"Пользователь {member_mentioned} было был лишён права использовать медиаконтент "
    if time:
        answer_text += f"на {time} минут\n"
    answer_text += f"администратором {admin_mentioned}"

    # Проверяем на наличие и корректность срока media_false
    if not time:
        # мение 30 секунд -- навсегда (время в минутах)
        time = 50000

    # Получаем конечную дату, до которой нужно замутить
    until_date = datetime.datetime.now() + datetime.timedelta(minutes=int(time))

    # Пытаемся забрать права у пользователя
    new_permissions = set_no_media_permissions()
    try:
        logging.info(f"{new_permissions.__dict__}")
        await message.chat.restrict(
            user_id=member_id, permissions=new_permissions, until_date=until_date
        )
        # Вносим информацию о муте в лог
        logging.info(
            f"Пользователю @{member_username} запрещено использовать медиаконтент до {until_date} "
            f"админом @{admin_username}"
        )
    # Если бот не может изменить права пользователя (администратора),
    # возникает ошибка BadRequest которую мы обрабатываем
    except Exception:
        # Отправляем сообщение
        await message.answer(
            f"Пользователь {member_mentioned} "
            "является администратором чата, изменить его права"
        )

        # Вносим информацию о муте в лог
        logging.info(f"Бот не смог забрать права у пользователя @{member_username}")

    # Отправляем сообщение
    await message.answer(text=answer_text)
    service_message = await message.reply("Сообщение самоуничтожится через 5 секунд")
    await asyncio.sleep(5)
    await message.reply_to_message.delete()
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(
    Command("media_true", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_restrict_members=True),
)
async def media_true_handler(message: types.Message, bot: Bot):
    (
        admin_username,
        admin_mentioned,
        chat_id,
        member_id,
        member_username,
        member_mentioned,
    ) = get_members_info(message)

    try:
        # Возвращаем пользователю возможность отправлять медиаконтент
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=member_id,
            permissions=set_new_user_approved_permissions(),
        )

        # Информируем об этом
        await message.answer(
            f"Пользователь {member_mentioned} "
            f"благодаря {admin_mentioned} может снова использовать медиаконтент"
        )
        logging.info(
            f"Пользователь @{member_username} благодаря @{admin_username} может снова использовать медиаконтент"
        )

        # Если бот не может забрать права пользователя (администратора),
        # возникает ошибка BadRequest которую мы обрабатываем
    except Exception:

        # Отправляем сообщение
        await message.answer(
            f"Пользователь {member_mentioned} "
            "является администратором чата, изменить его права"
        )
        # Вносим информацию о муте в лог
        logging.error(f"Бот не смог вернуть права пользователю @{member_username}")

    service_message = await message.reply("Сообщение самоуничтожится через 5 секунд.")
    await asyncio.sleep(5)
    await message.delete()
    await service_message.delete()
    await message.reply_to_message.delete()


# handler to promote and demoate users with optional arg for their custom title
@groups_moderate_router.message(
    Command("promote", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_promote_members=True),
)
async def promote_user(message: types.Message, bot: Bot):
    admin_username = message.from_user.username
    admin_mentioned = message.from_user.mention_html()
    member_id = message.reply_to_message.from_user.id
    member_username = message.reply_to_message.from_user.username
    member_mentioned = message.reply_to_message.from_user.mention_html()

    command_parse = re.compile(r"(!promote|/promote)( [\w+\D]+)?")
    parsed = command_parse.match(message.text)
    custom_title = parsed.group(2)

    try:
        await message.chat.promote(
            user_id=member_id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            custom_title=custom_title,
        )
        text = f"Користувач {member_mentioned} був підвищений до адміністратора адміністратором {admin_mentioned}"
        if custom_title:
            text += f" з посадою: {custom_title}"
            await bot.set_chat_administrator_custom_title(
                chat_id=message.chat.id, user_id=member_id, custom_title=custom_title
            )
        await message.answer(text)
        logging.info(
            f"Користувач @{member_username} був підвищений до адміністратора адміном @{admin_username}"
        )
    except Exception as e:
        logging.exception(e)
        await message.answer(
            f"Відбулася помилка під час підвищення користувача {member_mentioned} до адміністратора: {e}"
        )
        logging.info(f"Бот не зміг підвищити користувача @{member_username}")

        service_message = await message.reply(
            "Повідомлення самознищиться через 5 секунд."
        )
        await asyncio.sleep(5)
        await message.delete()
        await service_message.delete()


@groups_moderate_router.message(
    Command("title", prefix="/!", magic=F.args.len() > 0),
    F.reply_to_message.from_user.as_("member"),
    RatingFilter(rating=300),
)
@groups_moderate_router.message(
    Command("title", prefix="/!", magic=F.args.len() > 0),
    ~F.reply_to_message,
    F.from_user.as_("member_self"),
    RatingFilter(rating=100),
)
@groups_moderate_router.message(
    Command("title", prefix="/!", magic=F.args.len() > 0),
    ~F.reply_to_message,
    F.from_user.as_("member_self"),
    HasPermissionsFilter(can_promote_members=True),
)
@groups_moderate_router.message(
    Command("title", prefix="/!", magic=F.args.len() > 0),
    F.reply_to_message.from_user.as_("member"),
    HasPermissionsFilter(can_promote_members=True),
)
async def promote_with_title(
    message: types.Message,
    bot: Bot,
    repo: RequestsRepo,
    member: types.User | None = None,
    member_self: types.User | None = None,
):
    if member_self:
        member = member_self
        admin = await bot.get_me()

    elif member:
        admin = message.from_user
        target_rating = await repo.rating_users.get_rating_by_user_id(member.id)
        if target_rating > 100:
            return await message.answer(
                "Користувач має рейтинг більше 100, і має імунітет від цієї команди"
            )

    else:
        admin = message.from_user

    admin_username = admin.username
    admin_mentioned = admin.mention_html()

    member_id = member.id
    member_username = member.username
    member_mentioned = member.mention_html()

    command_parse = re.compile(r"(!title|/title)( [\w+\D]+)?")
    parsed = command_parse.match(message.text)
    custom_title = parsed.group(2)

    try:
        chat_member = await message.chat.get_member(member_id)
        if chat_member.status == "administrator":
            text = f"Користувачу {member_mentioned} було змінено посаду на {custom_title} адміністратором {admin_mentioned}"
            await message.chat.set_administrator_custom_title(
                user_id=member_id, custom_title=custom_title
            )
        else:
            text = f"Користувач {member_mentioned} був підвищений до адміністратора адміністратором {admin_mentioned} з посадою: {custom_title}"
            await message.chat.promote(
                user_id=member_id,
                can_invite_users=True,
            )
            await message.chat.set_administrator_custom_title(
                user_id=member_id, custom_title=custom_title
            )
        await message.answer(text)
        logging.info(
            f"Користувач @{member_username} був підвищений до адміністратора адміном @{admin_username}"
        )
    except Exception as e:
        logging.exception(e)
        await message.answer(
            f"Відбулася помилка під час підвищення користувача {member_mentioned} до адміністратора: {e}"
        )
        logging.info(f"Бот не зміг підвищити користувача @{member_username}")

        service_message = await message.reply(
            "Повідомлення самознищиться через 5 секунд."
        )
        await asyncio.sleep(5)
        await message.delete()
        await service_message.delete()


@groups_moderate_router.message(
    Command("title", prefix="/!"),
    ~F.reply_to_message,
    F.from_user.as_("member_self"),
    ~RatingFilter(rating=100),
)
async def not_enough_rating(message: types.Message):
    await message.answer("У вас недостатньо рейтингу для використання цієї команди.")


@groups_moderate_router.message(
    Command("demote", prefix="/!"),
    F.reply_to_message,
    HasPermissionsFilter(can_promote_members=True),
)
async def demote_user(message: types.Message):
    admin_username = message.from_user.username
    admin_mentioned = message.from_user.mention_html()
    member_id = message.reply_to_message.from_user.id
    member_username = message.reply_to_message.from_user.username
    member_mentioned = message.reply_to_message.from_user.mention_html()

    try:
        await message.chat.promote(
            user_id=member_id,
            can_invite_users=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_restrict_members=False,
            can_delete_messages=False,
        )
        await message.answer(
            f"Користувач {member_mentioned} був понижений до учасника адміністратором {admin_mentioned}"
        )
        logging.info(
            f"Користувач @{member_username} був понижений до учасника адміном @{admin_username}"
        )
    except Exception as e:
        logging.exception(e)
        await message.answer(
            f"Відбулася помилка під час пониження користувача {member_mentioned} до учасника: {e}"
        )
        logging.info(f"Бот не зміг понизити користувача @{member_username}")

        service_message = await message.reply(
            "Повідомлення самознищиться через 5 секунд."
        )
        await asyncio.sleep(5)
        await message.delete()
        await service_message.delete()
