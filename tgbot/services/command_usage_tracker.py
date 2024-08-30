from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import BotCommand, BotCommandScopeChatMember
from tgbot.misc.default_commands import commands_members, commands_admins

async def get_user_command_usage(storage: RedisStorage, bot_id: int, chat_id: int, user_id: int) -> dict:
    storage_key = StorageKey(bot_id, chat_id, user_id)
    data = await storage.get_data(storage_key)
    return data.get("command_usage", {})

async def update_command_usage(storage: RedisStorage, bot_id: int, chat_id: int, user_id: int, command: str):
    storage_key = StorageKey(bot_id, chat_id, user_id)
    data = await storage.get_data(storage_key)
    command_usage = data.get("command_usage", {})
    
    for cmd in commands_members.keys():
        command_usage.setdefault(cmd, 0)
    
    command_usage[command] = command_usage.get(command, 0) + 1
    await storage.update_data(storage_key, {"command_usage": command_usage})

async def get_sorted_commands(storage: RedisStorage, bot_id: int, chat_id: int, user_id: int, is_admin: bool) -> list[BotCommand]:
    command_usage = await get_user_command_usage(storage, bot_id, chat_id, user_id)
    available_commands = commands_admins if is_admin else commands_members
    
    def get_sort_key(cmd):
        usage_count = command_usage.get(cmd, 0)
        original_index = list(available_commands.keys()).index(cmd)
        return (-usage_count, original_index)
    
    sorted_command_names = sorted(available_commands.keys(), key=get_sort_key)
    
    return [BotCommand(command=name, description=available_commands[name]) for name in sorted_command_names]

async def update_user_commands(bot: Bot, chat_id: int, user_id: int, commands: list[BotCommand]):
    await bot.set_my_commands(
        commands,
        scope=BotCommandScopeChatMember(chat_id=chat_id, user_id=user_id)
    )