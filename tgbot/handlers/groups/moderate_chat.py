import asyncio
import datetime
import logging
import re

from aiogram import types, Bot, F, Router
from aiogram.filters import Command

from tgbot.filters.permissions import HasPermissionsFilter
from tgbot.misc.permissions import set_user_ro_permissions, \
    set_new_user_approved_permissions, set_no_media_permissions

restriction_time_regex = re.compile(r'(\b[1-9][0-9]*)([mhds]\b)')

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


@groups_moderate_router.message(Command("ro", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True))
async def read_only_mode(message: types.Message):
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
    command_parse = re.compile(r"(!ro|/ro) ?(\b[1-9][0-9]\w)? ?([\w+\D]+)?")
    parsed = command_parse.match(message.text)
    reason = parsed.group(3)
    # Проверяем на наличие и корректность срока RO.
    # Проверяем на наличие причины.
    reason = "без указания причины" if not reason else f"по причине: {reason}"
    # Получаем конечную дату, до которой нужно замутить
    ro_period = get_restriction_period(message.text)
    ro_end_date = message.date + datetime.timedelta(seconds=ro_period)

    try:
        # Пытаемся забрать права у пользователя
        await message.chat.restrict(
            user_id=member_id,
            permissions=set_user_ro_permissions(),
            until_date=ro_end_date,
        )

        # Отправляем сообщение
        await message.answer(
            f"Пользователю {member_mentioned} "
            f"было запрещено писать до {ro_end_date.strftime('%d.%m.%Y %H:%M')} "
            f"администратором {admin_mentioned} {reason} "
        )

        # Вносим информацию о муте в лог
        logging.info(
            f"Пользователю @{member_username} запрещено писать сообщения до {ro_end_date.strftime('%d.%m.%Y %H:%M')} админом @{admin_username} "
        )

    # Если бот не может замутить пользователя (администратора), возникает ошибка BadRequest которую мы обрабатываем
    except Exception as e:
        logging.exception(e)
        # Отправляем сообщение
        await message.answer(
            f"Пользователь {member_mentioned} "
            "является администратором чата, я не могу выдать ему RO"
        )
        # Вносим информацию о муте в лог
        logging.info(f"Бот не смог замутить пользователя @{member_username}")
    service_message = await message.reply(
        'Сообщение самоуничтожится через 5 секунд.'
    )

    await asyncio.sleep(5)
    # после прошедших 5 секунд, бот удаляет сообщение от администратора и от самого бота
    await message.delete()
    await service_message.delete()
    await message.reply_to_message.delete()


@groups_moderate_router.message(Command("unro", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True))
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
        f"Пользователь {member_mentioned} был размучен администратором {admin_mentioned}"
    )
    service_message = await message.reply("Сообщение самоуничтожится через 5 секунд.")

    # Не забываем про лог
    logging.info(
        f"Пользователь @{member_username} был размучен администратором @{admin_username}"
    )

    # Пауза 5 сек
    await asyncio.sleep(5)

    # Удаляем сообщения от бота и администратора
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(Command("ban", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True),
                                F.reply_to_message.sender_chat)
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
            f"Канал {member_fullname} был успешно забанен администратором {admin_mentioned}\n"
            f"Теперь владелец канала не сможет писать от имени любого из своих каналов"
        )

        logging.info(f"Канал {member_fullname} был забанен админом {admin_fullname}")
    except Exception as e:
        logging.info(f"Бот не смог забанить канал {member_fullname}")

    service_message = await message.answer("Сообщение самоуничтожится через 5 секунд.")

    await asyncio.sleep(5)

    await message.reply_to_message.delete()
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(Command("ban", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True))
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
            f"Пользователь {member_mentioned} был успешно забанен администратором {admin_mentioned}"
        )
        # Об успешном бане информируем разработчиков в лог
        logging.info(
            f"Пользователь {member_fullname} был забанен админом {admin_fullname}"
        )
    except Exception as e:
        # Отправляем сообщение
        logging.exception(e)
        await message.answer(
            f"Пользователь {member_mentioned} "
            "является администратором чата, я не могу выдать ему RO"
        )

        logging.info(f"Бот не смог забанить пользователя {member_fullname}")

    service_message = await message.answer("Сообщение самоуничтожится через 5 секунд.")

    # После чего засыпаем на 5 секунд
    await asyncio.sleep(5)
    # Не забываем удалить сообщение, на которое ссылался администратор
    await message.reply_to_message.delete()
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(Command("unban", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True))
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
        f"Канал {member_mentioned} был разбанен администратором {admin_mentioned}\n"
        f"Теперь владелец канала сможет писать от имени любого из своих каналов"
    )
    service_message = await message.reply("Сообщение самоуничтожится через 5 секунд.")

    logging.info(
        f"Канал @{member_username} был забанен админом @{admin_username}"
    )

    await asyncio.sleep(5)

    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(Command("unban", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True))
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
        f"Пользователь {member_mentioned} был разбанен администратором {admin_mentioned}"
    )
    service_message = await message.reply("Сообщение самоуничтожится через 5 секунд.")

    # Пауза 5 сек
    await asyncio.sleep(5)

    # Записываем в логи
    logging.info(
        f"Пользователь @{member_username} был забанен админом @{admin_username}"
    )

    # Удаляем сообщения
    await message.delete()
    await service_message.delete()


@groups_moderate_router.message(Command("media_false", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True))
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
    except Exception as err:
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


@groups_moderate_router.message(Command("media_true", prefix="/!"), F.reply_to_message,
                                HasPermissionsFilter(can_restrict_members=True))
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
    except Exception as e:

        # Отправляем сообщение
        await message.answer(
            f"Пользователь {member_mentioned} "
            "является администратором чата, изменить его права"
        )
        # Вносим информацию о муте в лог
        logging.error(f"Бот не смог вернуть права пользователю @{member_username}")

    service_message = await message.reply(f"Сообщение самоуничтожится через 5 секунд.")
    await asyncio.sleep(5)
    await message.delete()
    await service_message.delete()
    await message.reply_to_message.delete()
