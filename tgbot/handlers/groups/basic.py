from aiogram import F, Router, types
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.utils.markdown import hbold

from tgbot.keyboards.inline import start_markup

groups_basic_router = Router()

groups_basic_router.message.filter(
    F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP])
)


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

{header4}
/gay [ціль*] - Тест на гея
/biba - Перевірити бібу
/top_helpers - Топ хелперів
/title [титул*] - Встановити титул (можна відправити відповідь на повідомлення, щоб встановити титул користувачу)

{warning}
""".format(
        header1=hbold("Основні команди"),
        header2=hbold("Адміністрування"),
        header4=hbold("Інші команди"),
        warning=hbold(
            "У групах функціонал бота може відрізнятися.\n"
            "* - необов’язковий аргумент"
        ),
    )

    # Відправляємо список команд
    await message.reply(text=text, reply_markup=start_markup(in_group=True))
