import base64
import random
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import List, Literal, Optional

from aiogram.types import Message, ReactionTypeEmoji
from anthropic import AsyncAnthropic, types

from tgbot.services.markdown_parser import telegram_format


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


@dataclass
class AIConversation:
    messages: List[types.MessageParam] = field(default_factory=list)
    max_tokens: int = 380
    _model_name: str = "claude-3-opus-20240229"
    system_message: Optional[str] = None

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
        self, message: Message, ai_client: AsyncAnthropic, reply: Message | None = None
    ) -> int:
        sent_message = await message.answer(
            "⏳", reply_to_message_id=reply.message_id if reply else message.message_id
        )

        last_time = time.time()
        text = ""
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
                    await sent_message.edit_text(
                        telegram_format(text) + cont_symbol, parse_mode="HTML"
                    )
                    last_time = time.time()

        final_message = await stream.get_final_text()
        await sent_message.edit_text(telegram_format(final_message), parse_mode="HTML")
        await message.react(reaction=[ReactionTypeEmoji(emoji="👨‍💻")], is_big=True)
        return sent_message.message_id
