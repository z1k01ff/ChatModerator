import asyncio
import logging

from aiogram import Router, F, Bot, flags
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Audio, Voice, VideoNote, Video
from openai import AsyncOpenAI

from tgbot.services.ai_service.ai_conversation import AIConversation
from tgbot.services.ai_service.openai_provider import OpenAIProvider, convert_video_to_audio
from tgbot.services.ai_service.tts import convert_ogg_to_mp3, run_async


transcription_router = Router()
transcription_router.message.filter()
MAX_DOC_SIZE = 20 * 1024 * 1024

SUPPORTED_AUDIO_TYPES = [
    "audio/mpeg",
    "audio/mp4",
    "audio/mpeg",
    "audio/mpga",
    "audio/m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
]

@transcription_router.message(Command("transcribe"))
@transcription_router.message(Command("transcribe"), F.reply_to_message.voice.as_("voice"))
@transcription_router.message(Command("transcribe"), F.reply_to_message.audio.as_("audio"))
@transcription_router.message(Command("transcribe"), F.reply_to_message.video.as_("video"))
@transcription_router.message(Command("transcribe"), F.reply_to_message.video_note.as_("video_note"))
@flags.rate_limit(limit=300, key="transcribe", max_times=5)
@flags.override(user_id=362089194)
async def transcribe_audio(
    message: Message,
    openai_client: AsyncOpenAI,
    bot: Bot,
    state: FSMContext,
    voice: Voice|None = None,
    audio: Audio|None = None,
    video: Video|None = None,
    video_note: VideoNote|None = None,
):
    sent_message = await message.answer("⏳ Транскрибую аудіо...")

    if audio and audio.file_size > MAX_DOC_SIZE:
        return await message.answer("Аудіо занадто велике. Максимальний розмір 250 МБ.")
    if voice and voice.file_size > MAX_DOC_SIZE:
        return await message.answer("Голосове повідомлення занадто велике. Максимальний розмір 250 МБ.")
    if video and video.file_size > MAX_DOC_SIZE:
        return await message.answer("Відео занадто велике. Максимальний розмір 250 МБ.")
    if video_note and video_note.file_size > MAX_DOC_SIZE:
        return await message.answer("Відеоповідомлення занадто велике. Максимальний розмір 250 МБ.")

    if voice:
        duration = voice.duration
        audio = await bot.download(voice)
        file = await run_async(convert_ogg_to_mp3, audio)
    elif audio:
        duration = audio.duration
        if audio.mime_type == "audio/ogg":
            audio = await bot.download(audio)
            file = await run_async(convert_ogg_to_mp3, audio)
        elif audio.mime_type not in SUPPORTED_AUDIO_TYPES:
            return await message.answer("Непідтримуваний формат аудіо.")
        else:
            file = await bot.download(audio)
    elif video:
        duration = video.duration
        file = await bot.download(video)
        file = await run_async(convert_video_to_audio, file)
    elif video_note:
        duration = video_note.duration
        file = await bot.download(video_note)
    else:
        return await message.answer("Будь ласка, надішліть аудіо, відео або голосове повідомлення для транскрибування.")

    file.seek(0)
    try:
        response = await openai_client.audio.transcriptions.create(
            file=("audio.mp3", file),
            model="whisper-1",
            prompt=message.caption,
        )
        transcription = response.text
    except Exception as e:
        logging.error(f"Error during transcription: {e}")
        return await message.answer("Виникла помилка під час транскрибування. Будь ласка, спробуйте пізніше.")

    if not transcription:
        return await message.answer("Не вдалося розпізнати текст у аудіо.")

    # Split long transcriptions into multiple messages
    # Edit the first message
    await sent_message.edit_text(
        f"<b>🎙️ Транскрипція:</b>\n<blockquote expandable>{transcription[:4000]}</blockquote>",
        parse_mode="HTML"
    )

    # Send additional messages if the transcription is longer than 4000 characters
    for i in range(4000, len(transcription), 4000):
        await sent_message.reply(
            f"<b>🎙️ Транскрипція (продовження):</b>\n<blockquote expandable>{transcription[i:i+4000]}</blockquote>",
            parse_mode="HTML"
        )
        await asyncio.sleep(1)

    # Update token usage
    ai_conversation = AIConversation(
        bot=bot,
        ai_provider=OpenAIProvider(client=openai_client, model_name="whisper-1"),
        storage=state.storage,
        max_tokens=duration,
    )
    await ai_conversation.update_usage(
        message.chat.id,
        message.from_user.id,
        duration,
        ai_conversation.max_tokens,
    )
