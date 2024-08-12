from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import async_sessionmaker
import time
import logging

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.cache_profiles import get_profile_cached
async def apply_rating_inflation(bot: Bot, session_pool: async_sessionmaker, storage: RedisStorage):
    logging.info("Починається завдання інфляції рейтингу")
    
    current_time = int(time.time())
    reduced_ratings = []
    
    async with session_pool() as session:
        repo = RequestsRepo(session)
        # Отримуємо всі чати, де є бот
        bot_chats = await repo.rating_users.get_bot_chats() 
        
        for chat_id in bot_chats:
            # Отримуємо топ користувачів для цього конкретного чату
            top_users = await repo.rating_users.get_top_by_rating_for_chat(chat_id, 50) 
            
            chat_reduced_ratings = []
            for user_id, current_rating in top_users:
                # Перевіряємо, чи був користувач активним у цьому чаті за останній день
                last_activity_key = f"user_activity:{chat_id}:{user_id}"
                last_activity = await storage.redis.get(last_activity_key)
                
                if not last_activity or (current_time - int(last_activity)) >= 86400:  # 86400 секунд = 1 день
                    # Застосовуємо інфляцію: знижуємо на 1% або мінімум на 1 пункт
                    deduction = max(int(current_rating * 0.03), 1)
                    new_rating = max(current_rating - deduction, 0)  # Переконуємося, що рейтинг не стане від'ємним
                    
                    await repo.rating_users.update_rating_by_user_id_for_chat(user_id, chat_id, new_rating)
                    
                    # Отримуємо інформацію про профіль користувача
                    user_profile = await get_profile_cached(storage, chat_id, user_id, bot)
                    
                    if user_profile:
                        chat_reduced_ratings.append((user_profile, current_rating, new_rating))
                        logging.info(f"Застосовано інфляцію рейтингу для користувача {user_profile} в чаті {chat_id}. Старий рейтинг: {current_rating}, Новий рейтинг: {new_rating}")
                    else:
                        logging.info(f"Застосовано інфляцію рейтингу для користувача {user_id} в чаті {chat_id}. Старий рейтинг: {current_rating}, Новий рейтинг: {new_rating}. Не вдалося отримати профіль користувача.")
                else:
                    logging.info(f"Користувач {user_id} був активним у чаті {chat_id}. Інфляція не застосована. Поточний рейтинг: {current_rating}")
            
            if chat_reduced_ratings:
                reduced_ratings.append((chat_id, chat_reduced_ratings))

    # Формуємо повідомлення
    message = "📉 Щоденний звіт про інфляцію рейтингу 📉\n\n"
    for chat_id, chat_reduced_ratings in reduced_ratings:
        chat_name = await get_chat_name(bot, chat_id)
        message += f"Чат: {chat_name}\n"
        message += "Користувачі зі зниженим рейтингом (Топ 40):\n"
        for user_profile, old_rating, new_rating in sorted(chat_reduced_ratings, key=lambda x: x[2], reverse=True)[:40]:
            message += f"{user_profile}: {old_rating} → {new_rating} (-{old_rating - new_rating})\n"
        message += "\n"

    # Надсилаємо повідомлення
    for chat_id, _ in reduced_ratings:
        try:
            await bot.send_message(chat_id, message)
            logging.info(f"Надіслано звіт про інфляцію до чату {chat_id}")
        except Exception as e:
            logging.error(f"Не вдалося надіслати звіт про інфляцію до чату {chat_id}: {str(e)}")

    logging.info("Завершено завдання інфляції рейтингу")

async def get_chat_name(bot: Bot, chat_id: int) -> str:
    try:
        chat = await bot.get_chat(chat_id)
        return chat.title if chat.title else f"Чат {chat_id}"
    except Exception as e:
        logging.error(f"Не вдалося отримати назву чату для {chat_id}: {str(e)}")
        return f"Чат {chat_id}"

def setup_rating_inflation_task(scheduler: AsyncIOScheduler, bot: Bot, session_pool: async_sessionmaker, storage: RedisStorage):
    scheduler.add_job(
        apply_rating_inflation,
        trigger=CronTrigger(hour=13, minute=0),  # Run every day at 13:00
        # For testing purposes, run every min
        # trigger=CronTrigger(minute="*/1"),
        args=[bot, session_pool, storage],
        id='rating_inflation_task',
        replace_existing=True,
        # next_run_time=datetime.now() + timedelta(seconds=5),
    )
    logging.info("Rating inflation task scheduled")