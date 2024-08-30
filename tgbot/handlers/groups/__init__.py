from aiogram import F, Router
from aiogram.enums import ChatType

from .ai import ai_router
from .basic import groups_basic_router
from .casino import groups_casino_router
from .edit_chat import groups_chat_edit_router
from .moderate_chat import groups_moderate_router
from .rating import groups_rating_router
from .service_messages import service_message_router
from .payments import payment_router
from .transcribe import transcription_router
group_router = Router()
group_router.message.filter(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))


group_router.include_routers(
    groups_basic_router,
    groups_casino_router,
    groups_chat_edit_router,
    service_message_router,
    transcription_router,
    groups_moderate_router,
)


__all__ = ["group_router", "groups_rating_router", "ai_router", "payment_router"]
