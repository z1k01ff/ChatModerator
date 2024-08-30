import json
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from aiogram.enums import ChatType
from aiogram.types import Chat, Message
from aiogram.fsm.storage.redis import RedisStorage

class ChatAdminsMiddleware(BaseMiddleware):
    def __init__(self, storage: RedisStorage):
        self.storage = storage

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        event_chat: Chat = data.get("event_chat", None)
        if event_chat.type != ChatType.PRIVATE:
            chat_id = event_chat.id
            redis_key = f"chat_admins:{chat_id}"
            
            chat_admins_json = await self.storage.redis.get(redis_key)
            if not chat_admins_json:
                chat_admins = await event_chat.get_administrators()
                chat_admins_dict = {str(admin.user.id): admin.model_dump() for admin in chat_admins}
                await self.storage.redis.set(redis_key, json.dumps(chat_admins_dict), ex=3600)  # Cache for 1 hour
            else:
                chat_admins_dict = json.loads(chat_admins_json)
                chat_admins = {int(user_id): types.ChatMember(**admin_data) for user_id, admin_data in chat_admins_dict.items()}
                
            data['chat_admins'] = chat_admins

        return await handler(event, data)