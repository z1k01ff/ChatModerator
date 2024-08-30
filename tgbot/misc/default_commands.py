from aiogram import Bot, types
from aiogram.types import BotCommand

commands_members = {
    "ai": "ШІ відповідь",
    "casino": "Зіграти в казино",
    "title": "Встановити титул",
    "taro": "(AI*) Дізнатися прогноз Таро",
    "gay": "(AI*) Дізнатися, на скільки % користувач гей",
    "biba": "Дізнатися скільки см у користувача біба",
    "nation": "(AI*) Дізнатися національність користувача",
    "top": "Дізнатися топ користувачів",
    "rating": "Дізнатися рейтинг користувача",
    "help": "Інформація про бота",
    "history": "Історія чату",
}

commands_admins = {
    "provider_anthropic": "Змінити AI на Anthropic",
    "provider_openai": "Змінити AI на OpenAI",
    "cunning": "Увімкнути хитрого ШІ",
    "good": "Увімкнути доброго ШІ",
    "nasty": "Увімкнути поганого ШІ",
    "ro": "Замутити користувача",
    "unro": "Розмутити користувача",
    "ban": "Забанити користувача",
    "unban": "Розбанити користувача",
    "ban_me_please": "Забанити себе",
    "ban_me_really": "Забанити себе назавжди",
    "media_false": "Забороняє використання медіа",
    "media_true": "Дозволяє використання медіа",
    "promote": "Підвищити користувача",
    "demote": "Понизити користувача",
    "transcribe": "(AI*) Транскрибувати аудіо",
    **commands_members,
}
command_defaults = {"help": "Допоможіть мені"}


async def set_default_commands(bot: Bot):
    await bot.set_my_commands(
        [
            BotCommand(command=name, description=value)
            for name, value in command_defaults.items()
        ],
        scope=types.BotCommandScopeDefault(),
    )
    await bot.set_my_commands(
        [
            BotCommand(command=name, description=value)
            for name, value in commands_members.items()
        ],
        scope=types.BotCommandScopeAllGroupChats(),
    )
    await bot.set_my_commands(
        [
            BotCommand(command=name, description=value)
            for name, value in commands_admins.items()
        ],
        scope=types.BotCommandScopeAllChatAdministrators(),
    )
