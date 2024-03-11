import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage, StorageKey
from aiogram.utils.markdown import hlink


async def get_profile(group_id: int, chat_id: int, bot: Bot) -> str | bool:
    await asyncio.sleep(0.1)  # Simulating an async call
    try:
        logging.info(f"Getting profile for {chat_id}")
        member = await bot.get_chat_member(group_id, chat_id)
        if member.status not in ["member", "administrator", "creator", "restricted"]:
            return False
    except Exception:
        return False

    full_name = member.user.full_name
    if member.user.id == bot.id:
        full_name += " (bot)"

    return hlink(title=member.user.full_name, url=f"tg://user?id={chat_id}")


async def get_profile_cached(
    storage: RedisStorage, group_id: int, chat_id: int, bot: Bot
) -> str | bool:
    key = f"{group_id}_{chat_id}"
    storage_key = StorageKey(bot.id, group_id, group_id)
    now = datetime.now()

    group_data = await storage.get_data(storage_key)
    user_profiles = group_data.get("user_profiles", {})

    # Convert stored timestamp back to datetime for comparison
    update_time = user_profiles.get(key, {}).get("update_time", 0)
    update_time_datetime = datetime.fromtimestamp(update_time) if update_time else None

    # Check if the profile exists and is up to date
    if (
        key in user_profiles
        and update_time_datetime
        and (now - update_time_datetime).total_seconds() < 86400
    ):
        logging.info(f"Profile for {chat_id} is cached")
        return user_profiles[key]["profile"]

    # If profile is not present or outdated, fetch a new one
    profile = await get_profile(group_id, chat_id, bot)
    if profile:
        # Convert datetime to timestamp for storage
        user_profiles[key] = {"profile": profile, "update_time": now.timestamp()}

    # Update storage with new or updated profile data
    await storage.update_data(storage_key, {"user_profiles": user_profiles})
    return profile
