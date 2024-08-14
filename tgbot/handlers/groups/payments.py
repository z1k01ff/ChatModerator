from aiogram import Router, F, Bot
from aiogram.types import Message, PreCheckoutQuery

from tgbot.services.token_usage import TokenUsageManager


payment_router = Router()


@payment_router.pre_checkout_query()
async def checkout_handler(checkout_query: PreCheckoutQuery):
    await checkout_query.answer(ok=True)


@payment_router.message(F.successful_payment.total_amount >= 40)
async def star_payment(msg: Message, bot: Bot, state):
    usage_manager = TokenUsageManager(storage=state.storage, bot=bot)
    group_id = msg.successful_payment.invoice_payload
    await usage_manager.reset_usage(
        group_id=int(group_id),
        user_id=msg.from_user.id,
    )
    await bot.send_message(
        chat_id=group_id,
        text=f"Дякуємо {msg.from_user.full_name} за оплату використання штучного інтелекту!",
    )
