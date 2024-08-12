from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.redis import RedisStorage
import time

class UserActivityMiddleware(BaseMiddleware):
    def __init__(self, storage: RedisStorage):
        self.storage = storage

    async def __call__(self, handler, event, data):
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            chat_id = event.chat.id if isinstance(event, Message) else event.message.chat.id
            
            # Update last activity time in Redis for this specific chat
            await self.storage.redis.set(f"user_activity:{chat_id}:{user_id}", int(time.time()), ex=172800)  # TTL: 2 days
        
        return await handler(event, data)
    
    def setup(self, dp: Dispatcher):
        dp.message.middleware.register(self)