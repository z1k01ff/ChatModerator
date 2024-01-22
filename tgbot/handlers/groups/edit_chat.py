import io
import logging

from aiogram import types, Router, F
from aiogram.filters import Command

groups_chat_edit_router = Router()


@groups_chat_edit_router.message(Command("set_photo", prefix="/!"), F.admin)
async def set_new_photo(message: types.Message):
    source_message = message.reply_to_message
    photo = source_message.photo[-1]
    photo = await photo.download(destination=io.BytesIO())
    input_file = types.InputFile(photo)

    try:
        await message.chat.set_photo(photo=input_file)
        await message.reply("Фотографія була успішно оновлена.")
    except Exception as err:
        logging.exception(err)


@groups_chat_edit_router.message(Command("set_title", prefix="/!"), F.admin)
async def set_new_title(message: types.Message):
    source_message = message.reply_to_message
    title = source_message.text
    await message.chat.set_title(title=title)
    await message.reply("Назва була успішно оновлена.")


@groups_chat_edit_router.message(Command("set_description", prefix="/!"), F.admin)
async def set_new_description(message: types.Message):
    source_message = message.reply_to_message
    description = source_message.text
    await message.chat.set_description(description=description)
    await message.reply("Опис був успішно оновлений.")
