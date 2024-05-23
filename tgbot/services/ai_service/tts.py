from io import BytesIO
from typing import AsyncIterator
from aiogram.types import BufferedInputFile
import asyncio
from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs
import concurrent.futures

from pydub import AudioSegment


async def generate_speech(client: AsyncElevenLabs, text: str) -> AsyncIterator[bytes]:
    voice_id = "4nUxjX5jMlD8n4tsc9wu"

    return await client.generate(
        text=text,
        voice=voice_id,
        model="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.8,
            use_speaker_boost=True,
            style=0.7,
        ),
    )


async def run_async(func, *args):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, func, *args)
    return result


def convert_ogg_to_mp3(ogg_path: str):
    file = AudioSegment.from_file(ogg_path, format="ogg")
    return file.export(format="mp3", bitrate="128k")


def convert_mp3_to_ogg(mp3_path: str):
    file = AudioSegment.from_file(mp3_path, format="mp3")
    return file.export(format="ogg", bitrate="128k", codec="libopus")


async def prepare_audio_for_tg(audio: AsyncIterator[bytes]) -> BufferedInputFile:
    audio_bytes = b""
    async for chunk in audio:
        audio_bytes += chunk

    with BytesIO() as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_file.seek(0)
        file = await run_async(convert_mp3_to_ogg, tmp_file)
        bytes_audio = BytesIO(file.read())

    return BufferedInputFile(bytes_audio.getvalue(), "speech.ogg")


async def generate_tts(client: AsyncElevenLabs, text: str) -> BufferedInputFile:
    audio = await generate_speech(client, text.strip())
    return await prepare_audio_for_tg(audio)
