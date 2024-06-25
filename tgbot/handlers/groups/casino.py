import asyncio

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, User

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.broadcaster import send_message

groups_casino_router = Router()

HOURS = 60 * 60
MAX_CASINO_BET = 7


# Core logic for determining the win or loss outcome
async def process_dice_roll(
    message: types.Message,
    repo: RequestsRepo,
    user: User | None = None,
    rating_bet: int = 1,
):
    slots = {
        1: {"values": ("bar", "bar", "bar"), "coefficient": 7, "prize": "3X BAR"},
        22: {
            "values": ("grape", "grape", "grape"),
            "coefficient": 15,
            "prize": "🍇🍇🍇",
        },
        43: {
            "values": ("lemon", "lemon", "lemon"),
            "coefficient": 25,
            "prize": "🍋🍋🍋",
        },
        64: {
            "values": ("seven", "seven", "seven"),
            "coefficient": 50,
            "prize": "🔥ДЖЕКПОТ🔥",
        },
    }

    dice_value = (
        message.dice.value if message.dice else 0
    )  # Fallback to 0 if no dice value
    # await send_message(
    # bot=message.bot,
    # user_id=message.chat.id,
    # text=f"{user.full_name} витратив {rating_bet} рейтингу на казино. 🎰",
    # )

    if dice_value not in slots:
        await repo.rating_users.increment_rating_by_user_id(user.id, -rating_bet)
        await asyncio.sleep(6)
        await message.delete()

        return  # Exit if not a recognized dice value and not from a dice roll

    slot = slots[dice_value]
    coefficient = slot["coefficient"]
    prize = slot["prize"]

    if (
        message.forward_from
        or message.forward_sender_name
        or message.forward_from_message_id
    ):
        return

    added_rating = rating_bet * coefficient
    new_rating = await repo.rating_users.increment_rating_by_user_id(
        user.id, added_rating
    )

    success_message = f"Користувач {user.full_name} вибив {prize} і отримав {added_rating} рейтингу, тепер у нього {new_rating} рейтингу.\nВітаємо!"
    # await message.answer(success_message)
    await send_message(bot=message.bot, user_id=message.chat.id, text=success_message)


# Command handler for rolling the dice
@groups_casino_router.message(Command("casino"))
async def roll_dice_command(
    message: types.Message,
):
    await message.reply(
        text="Казино доступно тут: ",
        disable_web_page_preview=False,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎰 Зіграти!",
                        url="https://t.me/Latandbot/casino",
                    )
                ]
            ]
        ),
    )
