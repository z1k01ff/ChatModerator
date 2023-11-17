from aiogram import types, Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.utils.markdown import hbold


groups_basic_router = Router()


@groups_basic_router.message(CommandStart())
async def start(message: types.Message):
    await message.delete()


@groups_basic_router.message(Command("help", prefix="/!"))
async def help_cmd(message: types.Message):
    """
    Хендлер на команду /help
    Виводить список команд.
    """

    # Створюємо текст
    text = """{header1}
/start - Розпочати діалог зі мною
/help - Допомога по команді

{header2}
/ro - Встановити RO користувачу
/unro - Зняти RO у користувача
/ban - Забанити користувача
/unban - Розбанити користувача

{header3}
/set_photo - Змінити фотку
/set_title - Змінити назву
/set_description - Змінити опис

{header4}
/gay [ціль*] - Тест на гея
/biba - Перевірити бібу
/roll - Випадкове число

{warning}
""".format(
        header1=hbold("Основні команди"),
        header2=hbold("Адміністрування"),
        header3=hbold("Робота з групою"),
        header4=hbold("Інші команди"),
        warning=hbold(
            "У групах функціонал бота може відрізнятися.\n"
            "* - необов’язковий аргумент"
        )
    )

    # Відправляємо список команд
    await message.answer(text)
