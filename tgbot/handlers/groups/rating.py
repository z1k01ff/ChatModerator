import asyncio
import logging

from aiogram import Bot, F, Router, flags, types
from aiogram.enums import ChatType
from aiogram.filters import Command, or_f
from aiogram.utils.markdown import hlink
from async_lru import alru_cache

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.misc.reaction_change import get_reaction_change
from tgbot.services.rating import change_rating

groups_rating_router = Router()
groups_rating_router.message.filter(F.chat.type == ChatType.SUPERGROUP)

positive_emojis = ["👍", "❤", "🔥", "❤‍🔥"]
negative_emojis = ["👎", "🤡", "💩"]

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
for emoji in positive_emojis:
    ratings[emoji] = 1

for emoji in negative_emojis:
    ratings[emoji] = -1


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
async def get_top_helpers(m: types.Message, repo: RequestsRepo, bot):
    helpers = await repo.rating_users.get_top_by_rating(20)
    emoji_for_top = ["🦕", "🐙", "🐮", "🐻", "🐼", "🐰", "🦊", "🦁", "🙈", "🐤", "🐸"]

    helpers = [(user_id, rating) for user_id, rating in helpers]

    tops = "\n".join(
        [
            f"<b>{number}) {emoji_for_top[number - 1] if number <= len(emoji_for_top) else ''} "
            f"{await get_profile(user_id, bot)} "
            f"( {rating} )"
            f"</b>"
            for number, (user_id, rating) in enumerate(helpers, 1)
        ]
    )
    text = f"Топ Хелперів:\n{tops}"
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
    F.new_reaction[0].emoji.in_(positive_emojis).as_("positive_rating"),
)
@groups_rating_router.message_reaction(
    F.new_reaction[0].emoji.in_(negative_emojis).as_("negative_rating")
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
        else -1 if reaction_change == "negative" else 0
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


@alru_cache(maxsize=10)
async def get_profile(chat_id, bot) -> str:
    await asyncio.sleep(0.1)
    try:
        chat = await bot.get_chat(chat_id)
    except Exception:
        return "Відсутній"
    return hlink(title=chat.full_name, url=f"tg://user?id={chat_id}")
