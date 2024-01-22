from aiogram import types, Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.utils.markdown import hbold

from tgbot.keyboards.inline import start_markup

basic_router = Router()
basic_router.message.filter(F.chat.type == ChatType.PRIVATE)


@basic_router.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        f"Привіт, {hbold(message.from_user.full_name)}\n\n"
        "Я простий чат-менеджер з відкритим вихідним кодом, "
        "який пишеться учасниками чату з розробки ботів. "
        "Для повного функціоналу додай мене до групи ",
        reply_markup=start_markup,
    )


@basic_router.message(Command("help", prefix="/"))
async def help_cmd(message: types.Message):
    text = """{header1}
/start - Почати діалог зі мною
/help - Допомога по команді

{header2}
/gay [ціль*] -  Тест на гея
/biba - Перевірити бібу
/roll - Випадкове число

{warning}
""".format(
        header1=hbold("Основні команди"),
        header2=hbold("Інші команди"),
        warning=hbold(
            "У групах функціонал бота може відрізнятися.\n"
            "* - необов’язковий аргумент"
        ),
    )

    # Відправляємо список команд
    await message.answer(text)


@basic_router.callback_query(F.data == "help")
async def callback_handler(query: types.CallbackQuery):
    await query.answer()
    await help_cmd(query.message)
