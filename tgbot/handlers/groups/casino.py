import asyncio
import datetime
import logging

from aiogram import types, Router, F

from tgbot.misc.permissions import set_user_ro_permissions

groups_casino_router = Router()


@groups_casino_router.message(F.dice)
async def win_or_loss(message: types.Message):
    if message.dice.emoji != "🎰":
        return

    slots = {
        1: {"values": ("bar", "bar", "bar"), "time": 10, "prize": "3X BAR"},
        22: {"values": ("grape", "grape", "grape"), "time": 15, "prize": "🍇🍇🍇"},
        43: {"values": ("lemon", "lemon", "lemon"), "time": 20, "prize": "🍋🍋🍋"},
        64: {"values": ("seven", "seven", "seven"), "time": 25, "prize": "🔥ДЖЕКПОТ🔥"},
    }

    if message.dice.value not in slots:
        await asyncio.sleep(2.35)
        return await message.delete()

    slot = slots[message.dice.value]
    time = slot["time"]
    prize = slot["prize"]

    if message.forward_from:
        time += time
        prize += " а також обманював"

    until_date = datetime.datetime.now() + datetime.timedelta(minutes=time)
    username = message.from_user.username
    name = message.from_user.mention_html()

    try:
        await asyncio.sleep(1.67)
        await message.chat.restrict(
            user_id=message.from_user.id,
            permissions=set_user_ro_permissions(),
            until_date=until_date,
        )

        await message.answer(
            f"Користувач {name} "
            f"вибив {prize} і отримав "
            f"RO на {time} хвилин.\n"
            f"Вітаємо!"
        )

    except Exception:
        await message.answer(
            f"Адміністратор чату {name} виграв у казино {prize}"
        )

        logging.info(
            f"Бот не зміг замутити користувача @{username} ({name})"
            f"з причини: виграв у казино"
        )
    else:
        logging.info(
            f"Користувачу @{username} ({name}) заборонено писати повідомлення до {until_date} "
            f"з причини: виграв у казино"
        )

