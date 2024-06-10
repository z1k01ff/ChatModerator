from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.markdown import hcode

from tgbot.filters.admin import AdminFilter

admin_router = Router()

admin_router.message.filter(AdminFilter())


@admin_router.message(Command("refund"))
async def admin_refund_start(message: Message, command, bot: Bot):
    user_id, tx_id = command.args.split()
    result = await bot.refund_star_payment(int(user_id), tx_id)
    await message.answer(hcode(result), parse_mode="HTML")
