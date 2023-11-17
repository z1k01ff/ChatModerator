import asyncio

from aiogram import types, Router, F, flags
from aiogram.filters import Command
from async_lru import alru_cache

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.rating import caching_rating, change_rating

groups_rating_router = Router()

@groups_rating_router.message(Command('top_helpers'))
@flags.rate_limit(limit=30, key='top_helpers')
@flags.override(user_id=362089194)
async def get_top_helpers(m: types.Message, repo: RequestsRepo, bot):
    helpers = await repo.rating_users.get_top_by_rating()
    emoji_for_top = [
        '🦕', '🐙', '🐮', '🐻', '🐼', '🐰', '🦊', '🦁', '🙈', '🐤', '🐸'
    ]

    helpers = [(user_id, rating) for user_id, rating in helpers if rating > 0]

    tops = '\n'.join(
        [
            f'<b>{number}) {emoji_for_top[number - 1]} '
            f'{await get_profile(user_id, bot)} '
            f'( {rating} )'
            f'</b>'
            for number, (user_id, rating) in enumerate(helpers, 1)
        ]
    )
    text = f'Топ Хелперів:\n{tops}'
    await m.answer(text)

# Make sure to update the implementation details if necessary

@groups_rating_router.message(
    F.text.lower().in_(
        ['+', '➕', '👍', '-', '➖', '👎', 'спасибо', 'дякую', 'спасибо большое',
         "пошел нахуй", "иди нахуй"]
    ),
    F.reply_to_message
)
@flags.override(user_id=362089194)
@flags.rate_limit(limit=30, key='rating')
async def add_rating_handler(m: types.Message, repo:RequestsRepo, ratings_cache: dict):
    helper_id = m.reply_to_message.from_user.id  # айди хелпера
    user_id = m.from_user.id  # айди юзера, который поставил + или -
    message_id = m.reply_to_message.message_id

    if m.bot.id == helper_id or user_id == helper_id:
        return await m.delete()

    cached = caching_rating(helper_id, user_id, message_id, ratings_cache)
    if not cached:
        return await m.delete()

    mention_reply = m.reply_to_message.from_user.mention_html(m.reply_to_message.from_user.first_name)
    mention_from = m.from_user.mention_html(m.from_user.first_name)

    if helper_id == 362089194 and m.text in ['-', '👎', '➖']:
        await m.answer_photo(
            photo='https://memepedia.ru/wp-content/uploads/2019/02/uno-meme-1.jpg',
            caption='Вы не можете это сделать. Ваш удар был направлен против вас'
        )
        helper_id = m.from_user.id
        mention_reply = m.from_user.mention_html(m.from_user.first_name)
    ratings = {
        '+': 1, '➕': 1, '👍': 1, "спасибо": 1, "дякую": 1, "спасибо большое": 2,
        '-': -1, '➖': -1, '👎': -1, "пошел нахуй": -2, "иди нахуй": -2,
    }
    selected_rating = ratings.get(m.text)
    rating_user = await change_rating(helper_id, selected_rating, repo)

    if m.text in ['+', '➕', '👍', 'спасибо', 'дякую', 'спасибо большое']:
        text = f'{mention_from} <b>повысил рейтинг на {selected_rating} пользователю</b> {mention_reply} 😳 \n' \
               f'<b>Текущий рейтинг: {rating_user}</b>'
    else:
        text = f'{mention_from} <b>понизил рейтинг на {selected_rating} пользователю</b> {mention_reply} 😳 \n' \
               f'<b>Текущий рейтинг: {rating_user}</b>'

    await m.answer(text)




@alru_cache(maxsize=10)
async def get_profile(chat_id, bot) -> str:
    await asyncio.sleep(0.1)
    try:
        chat = await bot.get_chat(chat_id)
    except Exception:
        return 'Відсутній'
    return chat.full_name
