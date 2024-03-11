from aiogram.utils.keyboard import InlineKeyboardBuilder

"""Клавиатура, которая используется 
при стартовом сообщении. (!/start)"""


def start_markup(in_group: bool = False):
    markup = InlineKeyboardBuilder()
    if not in_group:
        markup.button(text="Список команд", callback_data="help")
        markup.button(text="Наш Чат", url="https://t.me/bot_devs_novice")

    markup.button(text="Мій код", url="https://github.com/BotfatherDev/ChatModerator")
    markup.adjust(1, 2)
    return markup.as_markup()
