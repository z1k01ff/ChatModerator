import logging

from aiogram import Bot, F, Router, flags, types
from aiogram.enums import ChatType
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from cachetools import TTLCache

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.misc.reaction_change import (
    NEGATIVE_EMOJIS,
    POSITIVE_EMOJIS,
    get_reaction_change,
)
from tgbot.services.cache_profiles import get_profile_cached
from tgbot.services.rating import change_rating

groups_rating_router = Router()
groups_rating_router.message.filter(F.chat.type == ChatType.SUPERGROUP)

cache = TTLCache(maxsize=10, ttl=60 * 60 * 24 * 7)
ratings = {
    "+": 1,
    "➕": 1,
    "👍": 1,
    "спасибо": 1,
    "дякую": 1,
    "спасибо большое": 2,
    "дякую велике": 2,
    "дуже дякую": 2,
    "дякую дуже": 2,
    "дякую величезне": 2,
    "-": -1,
    "➖": -1,
    "👎": -1,
    "пошел нахуй": -2,
    "иди нахуй": -2,
    "іді нахуй": -2,
    "пішов нахуй": -2,
}

# add positive emojis and negative emojis to the rating dict = 1 and rating = -1
for emoji in POSITIVE_EMOJIS:
    ratings[emoji] = 1

for emoji in NEGATIVE_EMOJIS:
    ratings[emoji] = -2


async def process_new_rating(
    rating_change: int,
    repo: RequestsRepo,
    helper_id: int,
    mention_from: str,
    mention_reply: str,
):
    rating_user = await change_rating(helper_id, rating_change, repo)

    if rating_change > 0:
        text = (
            f"{mention_from} <b>підвищив рейтинг на {rating_change} користувачу</b> {mention_reply} 😳 \n"
            f"<b>Поточний рейтинг: {rating_user}</b>"
        )
    else:
        text = (
            f"{mention_from} <b>знизив рейтинг на {-rating_change} користувачу</b> {mention_reply} 😳 \n"
            f"<b>Поточний рейтинг: {rating_user}</b>"
        )
    logging.info(text)
    return text


@groups_rating_router.message(Command("top_helpers"))
@flags.override(user_id=362089194)
@flags.rate_limit(limit=30, key="top_helpers")
async def get_top_helpers(m: types.Message, repo: RequestsRepo, bot, state: FSMContext):
    history_key = StorageKey(bot_id=bot.id, user_id=m.chat.id, chat_id=m.chat.id)
    state_data = await state.storage.get_data(key=history_key)
    previous_helpers = state_data.get("top_helpers", {})

    current_helpers = await repo.rating_users.get_top_by_rating(50)
    current_helpers_dict = {user_id: rating for user_id, rating in current_helpers}

    hetmans = []
    otamans = []
    cossacs = []
    pig_herder = []

    for user_id, rating in current_helpers:
        profile = await get_profile_cached(state.storage, m.chat.id, user_id, bot)
        if not profile:
            continue

        previous_rating = previous_helpers.get(str(user_id), rating)
        change = rating - previous_rating
        change = (
            f"⬆️ {change}" if change > 0 else f"🔻 {abs(change)}" if change < 0 else ""
        )
        helper_entry = (rating, change, profile)
        # Categorize helpers into leagues based on rating
        if rating > 300:
            hetmans.append(helper_entry)
        elif 100 < rating <= 300:
            otamans.append(helper_entry)
        elif 50 < rating <= 100:
            cossacs.append(helper_entry)
        elif len(pig_herder) < 10:
            pig_herder.append(helper_entry)

    await state.storage.update_data(
        key=history_key, data={"top_helpers": current_helpers_dict}
    )

    def format_league(league, league_name, emoji):
        formatted_entries = "\n".join(
            [
                f"<b>{number}) {emoji} " f"{profile} ( {rating} ) {change}</b>"
                for number, (rating, change, profile) in enumerate(league, 1)
            ]
        )
        return f"<b>{league_name}:</b>\n{formatted_entries}"

    text = "\n\n".join(
        [
            format_league(hetmans, "Гетьмани", "🦄"),
            format_league(otamans, "Отамани", "🐘"),
            format_league(cossacs, "Козаки", "🐥"),
            format_league(pig_herder, "Свинопаси", "👩‍🌾"),
        ]
    )

    text += """

<b>Права хелперів:</b>
- <b>🦄Гетьмани</b> можуть змінювати встановлювати собі і <b>🐥Козакам</b> і <b>👩‍🌾Свинопасам</b> кастомні титули.
- <b>🐘Отамани</b> можуть встановлювати кастомні титули тільки собі.
- Всі окрім <b>👩‍🌾Свинопасів</b> можуть користуватися командою /ai

<b>Правила:</b>
- Ставьте реакції на повідомлення, деякі позитивні реакції збільшують рейтинг на 1, деякі негативні зменшують на 3.
- Ви не можете змінювати рейтинг собі
- За 3 хвилини ви можете змінити рейтинг не більше 5 користувачам
- Ви не можете змінювати часто рейтинг одному користувачу
"""
    await m.answer(text, disable_notification=True)


# Make sure to update the implementation details if necessary
@groups_rating_router.message(
    F.text.lower().in_(ratings.keys()),
    F.reply_to_message,
    or_f(
        F.reply_to_message.from_user.id == F.from_user.id,
        F.bot.id == F.reply_to_message.from_user.id,
    ),
)
async def delete_rating_handler(m: types.Message):
    await m.delete()


@groups_rating_router.message(
    F.text.lower().in_(ratings.keys()),
    F.reply_to_message,
    F.reply_to_message.from_user.id != F.from_user.id,
)
@flags.override(user_id=362089194)
@flags.rate_limit(limit=180, key="rating", max_times=5)
@flags.rating_cache
async def add_rating_handler(m: types.Message, repo: RequestsRepo):
    helper_id = m.reply_to_message.from_user.id  # айди хелпера
    mention_reply = m.reply_to_message.from_user.mention_html(
        m.reply_to_message.from_user.first_name
    )
    mention_from = m.from_user.mention_html(m.from_user.first_name)

    if helper_id == 362089194 and m.text in ["-", "👎", "➖"]:
        await m.answer_photo(
            photo="https://memepedia.ru/wp-content/uploads/2019/02/uno-meme-1.jpg",
            caption="Ви не можете це зробити. Ваш удар був спрямований проти вас",
        )
        helper_id = m.from_user.id
        mention_reply = m.from_user.mention_html(m.from_user.first_name)

    rating_change = ratings.get(m.text, 1)  # type: ignore
    await process_new_rating(
        rating_change, repo, helper_id, mention_from, mention_reply
    )
    await m.react([types.ReactionTypeEmoji(emoji="✍")], is_big=True)


@groups_rating_router.message_reaction(
    F.new_reaction[0].emoji.in_(POSITIVE_EMOJIS).as_("positive_rating"),
)
@groups_rating_router.message_reaction(
    F.new_reaction[0].emoji.in_(NEGATIVE_EMOJIS).as_("negative_rating")
)
@flags.override(user_id=362089194)
@flags.rate_limit(limit=180, key="rating", max_times=5)
async def add_reaction_rating_handler(
    reaction: types.MessageReactionUpdated,
    repo: RequestsRepo,
    bot: Bot,
):
    reaction_change = get_reaction_change(
        new_reaction=reaction.new_reaction, old_reaction=reaction.old_reaction
    )
    rating_change = (
        1
        if reaction_change == "positive"
        else -3 if reaction_change == "negative" else 0
    )

    if not rating_change:
        return

    helper_id = await repo.message_user.get_user_id_by_message_id(
        reaction.chat.id, reaction.message_id
    )
    if not helper_id or helper_id == reaction.user.id:
        logging.info(
            f"User {reaction.user.id} tried to rate message {reaction.message_id} "
            f"but the message is not found in the database"
        )
        return
    helper = await bot.get_chat_member(reaction.chat.id, helper_id)

    await process_new_rating(
        rating_change,
        repo,
        helper_id,
        reaction.user.mention_html(reaction.user.first_name),
        helper.user.mention_html(helper.user.first_name),
    )


@groups_rating_router.message(
    Command("topup"),
    F.from_user.id == 362089194,
    F.reply_to_message.from_user.id.as_("target_id"),
)
async def topup_user(message: types.Message, target_id: int, repo: RequestsRepo):
    await repo.rating_users.increment_rating_by_user_id(target_id, 100)
    await message.answer("Рейтинг поповнено на 100")
