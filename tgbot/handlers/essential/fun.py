import random
import re

from aiogram import Router, flags, types
from aiogram.filters import Command

from tgbot.misc.parse_numbers import generate_num

fun_router = Router()


def determine_gender(name):
    # Lists of explicit names
    woman_names = ["Настенька"]

    # Women name endings
    women_name_endings = "|".join(
        [
            "sa",
            "са",
            "ta",
            "та",
            "ша",
            "sha",
            "на",
            "na",
            "ия",
            "ia",  # existing
            "va",
            "ва",
            "ya",
            "я",
            "ina",
            "ина",
            "ka",
            "ка",
            "la",
            "ла",  # Slavic languages
            "ra",
            "ра",
            "sia",
            "сия",
            "ga",
            "га",
            "da",
            "да",
            "nia",
            "ния",
            # Slavic languages
            "lie",
            "ly",
            "lee",
            "ley",
            "la",
            "le",
            "ette",
            "elle",
            "anne",  # English language
        ]
    )

    # Check explicit list and name suffixes
    if name in woman_names or re.search(
        f"\w*({women_name_endings})(\W|$)", name, re.IGNORECASE
    ):
        return "woman"
    else:
        return "man"


def select_emoji(length, is_biba):
    # Emojis for bibas, from smallest to largest
    biba_emojis = ["🥒", "🍌", "🌽", "🥖", "🌵", "🌴"]

    # Emojis for breasts, from smallest to largest
    breast_emojis = ["🍓", "🍊", "🍎", "🥭", "🍉", "🎃"]

    # Select the appropriate list of emojis
    emojis = biba_emojis if is_biba else breast_emojis

    # Select an emoji based on length
    for size, emoji in zip((1, 5, 10, 15, 20, 25), emojis):
        if length <= size:
            return emoji

    # If none of the sizes matched, return the largest emoji
    return emojis[-1]


@fun_router.message(Command("biba", prefix="!/"))
@flags.rate_limit(limit=60, key="fun")
async def biba(message: types.Message):
    """Хендлер, для обработки команды /biba или !biba

    В ответ, бот отправляет размер бибы

    Примеры:
        /biba
        /biba 10
        /biba 1-10
        /biba 10-1
        !biba
        !biba 10
        !biba 1-10
        !biba 10-1
    """
    # разбиваем сообщение на команду и аргументы через регулярное выражение
    command_parse = re.compile(r"(!biba|/biba) ?(-?\d*)?-?(\d+)?")
    parsed = command_parse.match(message.text)
    # генерируем размер бибы от 1 до 30 по умолчанию (если аргументы не переданы)
    length = generate_num(parsed.group(2), parsed.group(3), 1, 30)

    # если это ответ на сообщение, будем мерять бибу автора первичного сообщения
    # в противном случае, бибу того, кто использовал команду
    if message.reply_to_message:
        target = message.reply_to_message.from_user.mention_html()
    else:
        target = message.from_user.mention_html()

    gender = determine_gender(message.from_user.first_name)

    # Random chance to switch gender
    switch_chance = 20
    if random.randint(1, 100) <= switch_chance:
        gender = "man" if gender == "woman" else "woman"

    # Select an emoji for the biba or breast
    is_biba = gender == "man"
    emoji = select_emoji(length, is_biba)

    # Send message based on final gender
    if gender == "woman":
        await message.reply(f"{emoji} У {target} грудь {length // 5} размера.")
    else:
        # replace with your message for men
        await message.reply(f"{emoji} У {target} биба {length} см")
