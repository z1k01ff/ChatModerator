import asyncio
import datetime

from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.types import User

from tgbot.misc.permissions import set_user_ro_permissions

groups_casino_router = Router()


# Core logic for determining the win or loss outcome
async def process_dice_roll(message: types.Message, user: User | None = None):
    slots = {
        1: {"values": ("bar", "bar", "bar"), "time": 10, "prize": "3X BAR"},
        22: {"values": ("grape", "grape", "grape"), "time": 15, "prize": "🍇🍇🍇"},
        43: {"values": ("lemon", "lemon", "lemon"), "time": 20, "prize": "🍋🍋🍋"},
        64: {"values": ("seven", "seven", "seven"), "time": 25, "prize": "🔥ДЖЕКПОТ🔥"},
    }

    dice_value = (
        message.dice.value if message.dice else 0
    )  # Fallback to 0 if no dice value
    if dice_value not in slots:
        await asyncio.sleep(5.35)
        if message.dice:  # If called from a dice roll, delete the message
            return await message.delete()
        return  # Exit if not a recognized dice value and not from a dice roll

    slot = slots[dice_value]
    time = slot["time"]
    prize = slot["prize"]

    if message.forward_from:
        time *= 2  # Doubling the time if the message was forwarded
        prize += " а також обманював"

    until_date = datetime.datetime.now() + datetime.timedelta(minutes=time)

    try:
        user = user or message.from_user
        await asyncio.sleep(4.67)
        await message.chat.restrict(
            user_id=user.id,
            permissions=set_user_ro_permissions(),
            until_date=until_date,
        )
        success_message = f"Користувач {user.full_name} вибив {prize} і отримав RO на {time} хвилин.\nВітаємо!"
        await message.answer(success_message)
    except Exception as e:
        error_message = f"Помилка при обмеженні користувача: {e}"
        await message.answer(error_message)


# Handler for dice rolls with the slot machine emoji
@groups_casino_router.message(F.dice.emoji == "🎰")
async def win_or_loss(message: types.Message):
    await process_dice_roll(message)


# Command handler for rolling the dice
@groups_casino_router.message(Command("casino"))
async def roll_dice_command(message: types.Message, bot: Bot):
    await message.delete()  # Delete the command message after processing
    sent_message = await bot.send_dice(message.chat.id, emoji="🎰")
    await process_dice_roll(sent_message, user=message.from_user)
