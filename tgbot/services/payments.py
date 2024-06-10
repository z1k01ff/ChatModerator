from aiogram import Bot
from aiogram.types import LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def create_invoice(bot: Bot, usage_usd: float, group_id: int):
    return await bot.create_invoice_link(
        title="AI Usage",
        description=f"Chatbot AI usage for ${usage_usd:.2f}",
        payload=str(group_id),
        provider_token="",
        currency="XTR",
        prices=[
            LabeledPrice(label="label", amount=40),
        ],
    )


async def payment_keyboard(bot: Bot, usage_usd: float, group_id: int):
    kbd = InlineKeyboardBuilder()
    invoice = await create_invoice(bot, usage_usd, group_id)
    kbd.button(
        text="Оплатити 40 ⭐️ за ШІ",
        url=invoice,
    )
    return kbd.as_markup()
