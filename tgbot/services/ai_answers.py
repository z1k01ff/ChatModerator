import base64
import logging
import random
import time
from dataclasses import dataclass
from io import BytesIO
from typing import List, Literal, Optional

from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, ReactionTypeEmoji
from anthropic import AsyncAnthropic, types

from tgbot.services.token_usage import TokenUsageManager
from chatgpt_md_converter import telegram_format


@dataclass
class AIMedia:
    photo: BytesIO
    mime_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"] = (
        "image/jpeg"
    )

    def _prepare_photo(self) -> str:
        return base64.b64encode(self.photo.getvalue()).decode("utf-8")

    def render_content(
        self,
        text: str | None = None,
    ) -> list:
        content = [
            types.ImageBlockParam(
                type="image",
                source={
                    "type": "base64",
                    "media_type": self.mime_type,
                    "data": self._prepare_photo(),
                },
            ),
        ]
        if text:
            content.append(types.TextBlockParam(text=text, type="text"))  # type: ignore

        return content


class AIConversation(TokenUsageManager):
    def __init__(
        self,
        storage: RedisStorage,
        bot: Bot,
        messages: List[types.MessageParam] | None = None,
        max_tokens: int = 450,
        model_name: str = "claude-3-opus-20240229",
        system_message: Optional[str] = None,
    ):
        super().__init__(storage, bot)
        self.messages: list[types.MessageParam] = messages or []
        self.max_tokens = max_tokens
        self._model_name = model_name
        self.system_message = system_message
        self.conversation_log = ""

    def add_message(
        self,
        role: Literal["user", "assistant"],
        text: str | None = None,
        photo: list | None = None,
    ):
        if photo:
            self.messages.append(types.MessageParam(role=role, content=photo))
        else:
            self.messages.append(types.MessageParam(role=role, content=text))  # type: ignore
        self.conversation_log += f"{role}: {text if text else 'photo'}\n"

    def _prepare_photo(self, photo: BytesIO) -> str:
        return base64.b64encode(photo.getvalue()).decode("utf-8")

    def add_user_message(
        self, text: str | None = None, ai_media: AIMedia | None = None
    ):
        if ai_media:
            self.add_message("user", text, photo=ai_media.render_content(text))
        else:
            self.add_message("user", text=text)

    def add_assistant_message(self, text: str | None = None):
        self.add_message("assistant", text=text)

    async def answer_with_ai(
        self,
        message: Message,
        sent_message: Message,
        ai_client: AsyncAnthropic,
        notification: str | None = None,
        apply_formatting: bool = True,
    ) -> int:
        last_time = time.time()
        text = ""

        if not self.messages:
            await sent_message.edit_text(
                "🤖 Не знаю на що відповідати:)",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            # log all messages to send (no need to show photo content, since its bytes):
            logging.info(self.system_message + "\n\n" + self.conversation_log)
            pass

        async with ai_client.messages.stream(
            max_tokens=self.max_tokens,
            model=self._model_name,
            messages=[message for message in self.messages],
            system=self.system_message,  # type: ignore
        ) as stream:
            async for partial_text in stream.text_stream:
                text += partial_text
                if time.time() - last_time > 5:
                    cont_symbol = random.choice(["▌", "█"])
                    formatted_text = telegram_format(text) if apply_formatting else text
                    await sent_message.edit_text(
                        f"{notification}\n\n{formatted_text}{cont_symbol}",
                        parse_mode="HTML" if apply_formatting else None,
                        disable_web_page_preview=True,
                    )
                    last_time = time.time()

        final_text = await stream.get_final_text()
        formatted_text = telegram_format(final_text) if apply_formatting else final_text
        await sent_message.edit_text(
            f"{notification}\n\n{formatted_text}",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        logging.info(f"AI: {final_text}")
        await message.react(reaction=[ReactionTypeEmoji(emoji="👨‍💻")], is_big=True)
        return (await stream.get_final_message()).usage.input_tokens
