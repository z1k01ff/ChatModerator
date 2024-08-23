import base64
import logging
import os
import tempfile
from typing import AsyncGenerator, List, Optional
from io import BytesIO
import cv2
from openai import AsyncOpenAI
from aiogram import types
from tgbot.services.ai_service.base_provider import AIMediaBase, AIProviderBase
import asyncio
import concurrent.futures
from pydub import AudioSegment

MAX_VIDEO_SIZE = 20 * 1024 * 1024  # 20 MB

async def run_async(func, *args):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, func, *args)
    return result

def convert_video_to_audio(video_file: BytesIO) -> BytesIO:
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video_file:
        temp_video_file.write(video_file.getvalue())
        temp_video_file_path = temp_video_file.name

    audio = AudioSegment.from_file(temp_video_file_path, format="mp4")
    mp3_file = BytesIO()
    audio.export(mp3_file, format="mp3", bitrate="128k")
    mp3_file.seek(0)

    os.unlink(temp_video_file_path)
    return mp3_file

class OpenAIMedia(AIMediaBase):
    def __init__(self, photo: Optional[BytesIO] = None, video: Optional[BytesIO] = None, animation: Optional[BytesIO] = None, mime_type: Optional[str] = None, transcription: Optional[str] = None):
        super().__init__(photo)
        self.video = video
        self.animation = animation
        self.mime_type = mime_type
        self.transcription = transcription

    def prepare_photo(self) -> str:
        return base64.b64encode(self.photo.getvalue()).decode("utf-8")

    def prepare_video_frames(self, file: BytesIO, max_frames: int = 30) -> List[str]:
        file.seek(0)
        video_bytes = file.read()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(video_bytes)
            temp_file_path = temp_file.name

        def process_video():
            cap = cv2.VideoCapture(temp_file_path)
            frames = []
            frame_count = 0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            step = max(0.7, total_frames // max_frames)

            while len(frames) < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_count % step == 0:
                    _, buffer = cv2.imencode('.jpg', frame)
                    base64_frame = base64.b64encode(buffer).decode('utf-8')
                    frames.append(base64_frame)
                frame_count += 1

            cap.release()
            return frames

        frames = process_video()
        os.unlink(temp_file_path)
        return frames

    def render_content(self, text: Optional[str] = None) -> list:
        content = []
        if self.transcription:
            content.append({"type": "text", "text": f"Video transcription: {self.transcription}"})
        
        if text:
            content.append({"type": "text", "text": text})

        if self.photo:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{self.prepare_photo()}"
                },
            })
        elif self.video or self.animation:
            file = self.video or self.animation
            frames = self.prepare_video_frames(file)
            for frame in frames:
                content.append({
                    "type": "image_url",
                    "resize": 768,
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame}"
                    },
                })
            logging.info(f"Added {len(frames)} frames to the content")

        return content

class OpenAIProvider(AIProviderBase):
    def __init__(self, client: AsyncOpenAI, model_name: str = "gpt-4o"):
        super().__init__(media_class=OpenAIMedia)
        self.client = client
        self.model_name = model_name

    async def generate_response(
        self,
        messages: List[dict],
        max_tokens: int,
        system_message: Optional[str] = None,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        if system_message:
            messages.insert(0, {"role": "system", "content": system_message})

        chat_completion = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        async for chunk in chat_completion:
            if chunk.choices and chunk.choices[0].delta:
                yield chunk.choices[0].delta.content or ""

    async def process_video_media(self, message: types.Message) -> Optional[OpenAIMedia]:
        async def download_media(file: types.File):
            return await message.bot.download(file)

        async def process_message(msg: types.Message) -> Optional[OpenAIMedia]:
            if msg.video and msg.video.file_size <= MAX_VIDEO_SIZE:
                video_file = await msg.bot.get_file(msg.video.file_id)
                video_data = await download_media(video_file)
                audio_data = convert_video_to_audio(video_data)
                transcription = await self.transcribe_audio(audio_data)
                return OpenAIMedia(video=video_data, mime_type=msg.video.mime_type, transcription=transcription)
            elif msg.animation and msg.animation.file_size <= MAX_VIDEO_SIZE:
                animation_file = await msg.bot.get_file(msg.animation.file_id)
                animation_data = await download_media(animation_file)
                return OpenAIMedia(animation=animation_data, mime_type=msg.animation.mime_type)
            return None

        # First, try to process the media in the current message
        result = await process_message(message)
        if result:
            logging.info("Processing current message media")
            return result

        # If no media in the current message, check the replied message
        if message.reply_to_message:
            logging.info("Processing replied message media")
            return await process_message(message.reply_to_message)

        return None

    async def transcribe_audio(self, audio_file: BytesIO) -> str:
        audio_file.seek(0)
        transcription = await self.client.audio.transcriptions.create(
            file=("audio.mp3", audio_file),
            model="whisper-1",
        )
        return transcription.text