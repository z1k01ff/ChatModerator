import logging

from aiogram import Bot, F, Router, flags, types
from aiogram.enums import ChatType
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from cachetools import TTLCache

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.rating import RatingFilter
from tgbot.middlewares.ratings_cache import RatingCacheReactionMiddleware
from tgbot.services.rating import (
    NEGATIVE_EMOJIS,
    POSITIVE_EMOJIS,
    reaction_rating_calculator,
)
from tgbot.services.cache_profiles import get_profile_cached
from tgbot.services.rating import change_rating

groups_rating_router = Router()
groups_rating_router.message.filter(F.chat.type == ChatType.SUPERGROUP)
groups_rating_router.message_reaction.middleware(RatingCacheReactionMiddleware())

cache = TTLCache(maxsize=10, ttl=60 * 60 * 24 * 7)


async def process_new_rating(
    rating_change: int,
    repo: RequestsRepo,
    helper_id: int,
    mention_from: str,
    mention_reply: str,
) -> tuple[int, str] | None:
    previous_rating, new_rating = await change_rating(helper_id, rating_change, repo)

    if rating_change > 0:
        text = (
            f"{mention_from} <b>підвищив рейтинг на {rating_change} користувачу</b> {mention_reply} 😳 \n"
            f"<b>Поточний рейтинг: {new_rating}</b>"
        )
    else:
        text = (
            f"{mention_from} <b>знизив рейтинг на {-rating_change} користувачу</b> {mention_reply} 😳 \n"
            f"<b>Поточний рейтинг: {new_rating}</b>"
        )
    logging.info(text)

    milestones = [50, 100, 300, 600, 1000]
    for milestone in milestones:
        if previous_rating < milestone <= new_rating:
            if milestone == 1000:
                return new_rating, "👑 Король"
            elif milestone == 600:
                return new_rating, "🧙‍♂️ Чаклун"
            elif milestone == 300:
                return new_rating, "🦄 Гетьман"
            elif milestone == 100:
                return new_rating, "🐘 Отаман"
            elif milestone == 50:
                return new_rating, "🐥 Козак"


@groups_rating_router.message(Command("top_helpers"))
@flags.override(user_id=362089194)
@flags.rate_limit(limit=30, key="top_helpers", chat=True)
async def get_top_helpers(m: types.Message, repo: RequestsRepo, bot, state: FSMContext):
    history_key = StorageKey(bot_id=bot.id, user_id=m.chat.id, chat_id=m.chat.id)
    state_data = await state.storage.get_data(key=history_key)
    previous_helpers = state_data.get("top_helpers", {})

    current_helpers = await repo.rating_users.get_top_by_rating(50)
    current_helpers_dict = {user_id: rating for user_id, rating in current_helpers}

    kings = []
    sorcerers = []
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
        if rating >= 1000:
            kings.append(helper_entry)
        elif 600 <= rating < 1000:
            sorcerers.append(helper_entry)
        elif 300 <= rating < 600:
            hetmans.append(helper_entry)
        elif 100 <= rating < 300:
            otamans.append(helper_entry)
        elif 50 <= rating <= 100:
            cossacs.append(helper_entry)
        elif len(pig_herder) < 10:
            pig_herder.append(helper_entry)

    await state.storage.update_data(
        key=history_key, data={"top_helpers": current_helpers_dict}
    )

    def format_league(league, league_name, emoji):
        if not league:
            return ""

        formatted_entries = "\n".join(
            [
                f"<b>{number}) {emoji} " f"{profile} ( {rating} ) {change}</b>"
                for number, (rating, change, profile) in enumerate(league, 1)
            ]
        )
        return f"<b>{league_name}:</b>\n{formatted_entries}"

    text = "\n\n".join(
        [
            format_league(kings, "Королі", "👑"),
            format_league(sorcerers, "Чаклуни", "🧙‍♂️"),
            format_league(hetmans, "Гетьмани", "🦄"),
            format_league(otamans, "Отамани", "🐘"),
            format_league(cossacs, "Козаки", "🐥"),
            format_league(pig_herder, "Свинопаси", "👩‍🌾"),
        ]
    )

    # - <b>👑Королі</b>
    text += """
<b>Права хелперів:</b>
- <b>🧙‍♂️Чаклуни</b> можуть використовувати команду /history, щоб отримати які теми обговорювались за останні 200 повідомлень.
- <b>🦄Гетьмани</b> можуть змінювати встановлювати собі, <b>🐥Козакам</b> і <b>👩‍🌾Свинопасам</b> кастомні титули.
- <b>🐘Отамани</b> можуть встановлювати кастомні титули тільки собі.
- <b>👩‍🌾Свинопаси</b> не можуть користуватися командою /ai
- <b>👩‍🌾Свинопаси</b> не мають права брати участь у казино /casino.

<b>Правила:</b>
- Ставьте реакції на повідомлення, деякі позитивні реакції збільшують рейтинг на 1, деякі негативні зменшують на 3.
- Ви не можете змінювати рейтинг собі
- За 3 хвилини ви можете змінити рейтинг не більше 5 користувачам
- Ви не можете змінювати часто рейтинг одному користувачу

<b>Таблиця виграшів /casino:</b>
- 3X BAR коефіцієнт виграшу 7.
- 🍇🍇🍇 коефіцієнт виграшу 15
- 🍋🍋🍋 коефіцієнт виграшу 20
🔥ДЖЕКПОТ🔥 коефіцієнт виграшу 50
"""
    await m.answer(text, disable_notification=True)


@groups_rating_router.message_reaction(
    or_f(
        F.new_reaction[0].emoji.in_(POSITIVE_EMOJIS),
        F.old_reaction[0].emoji.in_(POSITIVE_EMOJIS),
    ),
)
@groups_rating_router.message_reaction(
    or_f(
        F.new_reaction[0].emoji.in_(NEGATIVE_EMOJIS),
        F.old_reaction[0].emoji.in_(NEGATIVE_EMOJIS),
    ),
    RatingFilter(rating=50),
)
@flags.override(user_id=362089194)
@flags.rate_limit(limit=180, key="rating", max_times=5)
async def add_reaction_rating_handler(
    reaction: types.MessageReactionUpdated,
    repo: RequestsRepo,
    bot: Bot,
    helper_id: int,
):
    rating_change = await reaction_rating_calculator(
        reaction, repo, helper_id, reaction.user.id
    )
    if not helper_id or helper_id == reaction.user.id:
        logging.info(
            f"User {reaction.user.id} tried to rate message {reaction.message_id} "
            f"but the message is not found in the database"
        )
        return
    helper = await bot.get_chat_member(reaction.chat.id, helper_id)

    upgraded = await process_new_rating(
        rating_change,
        repo,
        helper_id,
        reaction.user.mention_html(reaction.user.first_name),
        helper.user.mention_html(helper.user.first_name),
    )
    if upgraded:
        new_rating, title = upgraded
        await bot.send_message(
            reaction.chat.id,
            f"🎉 Вітаємо {helper.user.mention_html(helper.user.first_name)}! Досягнутий рівень: {title}! 🎉",
        )


@groups_rating_router.message(
    Command("topup"),
    F.from_user.id == 362089194,
    F.reply_to_message.from_user.id.as_("target_id"),
)
async def topup_user(message: types.Message, target_id: int, repo: RequestsRepo):
    await repo.rating_users.increment_rating_by_user_id(target_id, 100)
    await message.answer("Рейтинг поповнено на 100")
