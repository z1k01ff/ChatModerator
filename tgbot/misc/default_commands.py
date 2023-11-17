from aiogram import types, Bot
from aiogram.types import BotCommand


async def set_default_commands(bot: Bot):
    """
    Ставит стандартные команды бота
    """

    commands_members = {
        "gay": "Дізнатися, на скільки % користувач гей",
        "biba": "Дізнатися скільки см у користувача біба",
        "top_helpers": "Дізнатися топ хелперів"
    }

    command_defaults = {
        'help': 'Допоможіть мені'
    }

    commands_admins = {
        "ro": "Замутити користувача",
        "unro": "Розмутити користувача",
        "ban": "Забанити користувача",
        "unban": "Розбанити користувача",
        "set_photo": "Встановити фото в чаті",
        "set_title": "Встановити назву групи",
        "set_description": "Встановити опис групи",
        "media_false": "Забороняє використання медіа",
        "media_true": "Дозволяє використання медіа",
        "promote": "Підвищити користувача",
        "demote": "Понизити користувача",
        **commands_members
    }

    await bot.set_my_commands(
        [BotCommand(command=name, description=value) for name, value in command_defaults.items()],
        scope=types.BotCommandScopeDefault()
    )
    await bot.set_my_commands(
        [BotCommand(command=name, description=value) for name, value in commands_members.items()],
        scope=types.BotCommandScopeAllGroupChats()
    )
    await bot.set_my_commands(
        [BotCommand(command=name, description=value) for name, value in commands_admins.items()],
        scope=types.BotCommandScopeAllChatAdministrators()
    )
