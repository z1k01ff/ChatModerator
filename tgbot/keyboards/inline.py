from aiogram.utils.keyboard import InlineKeyboardBuilder

"""Клавиатура, которая используется 
при стартовом сообщении. (!/start)"""


def start_markup():
    markup = InlineKeyboardBuilder()
    markup.button(text="Список команд", callback_data="help")
    markup.button(text="Мій код", url="https://github.com/BotfatherDev/ChatModerator")
    markup.button(text="Чат", url="https://t.me/bot_devs_novice")
    return markup.as_markup()
