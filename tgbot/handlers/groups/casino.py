import asyncio

from aiogram import Bot, F, Router, types, flags
from aiogram.filters import Command, CommandObject
from aiogram.types import User

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.rating import RatingFilter

groups_casino_router = Router()

HOURS = 60 * 60


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
    await message.answer(
        f"{user.full_name} витратив {rating_bet} рейтингу на казино. 🎰"
    )

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
    await message.answer(success_message)


# Handler for dice rolls with the slot machine emoji
@groups_casino_router.message(F.dice.emoji == "🎰", RatingFilter(50))
@flags.rate_limit(limit=2 * HOURS, key="casino", max_times=3)
async def win_or_loss(message: types.Message, repo: RequestsRepo):
    await process_dice_roll(message, user=message.from_user, rating_bet=1, repo=repo)


# Command handler for rolling the dice
@groups_casino_router.message(
    Command("casino", magic=F.args.regexp(r"(\d+)")), RatingFilter(rating=50)
)
@groups_casino_router.message(Command("casino", magic=~F.args), RatingFilter(rating=50))
@flags.rate_limit(limit=2 * HOURS, key="casino", max_times=3)
async def roll_dice_command(
    message: types.Message,
    bot: Bot,
    repo: RequestsRepo,
    command: CommandObject,
):
    sent_message = await bot.send_dice(message.chat.id, emoji="🎰")
    await message.delete()
    rating_bet = abs(min(int(command.args) if command.args else 1, 13))
    await process_dice_roll(
        message=sent_message, user=message.from_user, rating_bet=rating_bet, repo=repo
    )
