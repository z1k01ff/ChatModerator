from aiogram import Router, F
from aiogram.enums import ChatType

from .basic import groups_basic_router
from .casino import groups_casino_router
from .edit_chat import groups_chat_edit_router
from .moderate_chat import groups_moderate_router
from .rating import groups_rating_router
from .service_messages import service_message_router

group_router = Router()
group_router.message.filter(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))

group_router.include_routers(
    groups_basic_router,
    groups_casino_router,
    groups_chat_edit_router,
    service_message_router,
    groups_rating_router,
    groups_moderate_router,
)
