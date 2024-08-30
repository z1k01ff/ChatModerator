from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.enums import ChatType
from aiogram.filters import CommandObject
from aiogram.types import Chat, Message
from aiogram.fsm.storage.redis import RedisStorage

from tgbot.services.command_usage_tracker import (
    update_command_usage,
    get_sorted_commands,
    update_user_commands,
)
from tgbot.filters.permissions import ChatMemberType, is_user_admin

class CommandUsageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        command: CommandObject = data.get("command")
        is_admin: bool = data.get("is_admin", None)
        event_from_chat: Chat|None = data.get("event_chat", None)

        if command and result is not UNHANDLED and event_from_chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            storage: RedisStorage = data["storage"]
            bot: Bot = data["bot"]
            chat_admins: dict[int, ChatMemberType] = data.get("chat_admins", {})

            is_admin = await is_user_admin(chat_admins, event.from_user.id)
            await update_command_usage(
                storage, bot.id, event.chat.id, event.from_user.id, command.command
            )

            sorted_commands = await get_sorted_commands(
                storage, bot.id, event.chat.id, event.from_user.id, is_admin
            )

            await update_user_commands(
                bot, event.chat.id, event.from_user.id, sorted_commands
            )

        return result
