import logging
import random
import time
from typing import Optional

from aiogram import Bot
from aiogram.types import Message, ReactionTypeEmoji

from tgbot.services.token_usage import TokenUsageManager
from tgbot.services.ai_service.message_handler import MessageHandler
from tgbot.services.ai_service.anthropic_provider import AIMediaBase, AIProviderBase
from chatgpt_md_converter import telegram_format


class AIConversation(TokenUsageManager):
    def __init__(
        self,
        storage,
        bot: Bot,
        ai_provider: AIProviderBase,
        max_tokens: int = 450,
        system_message: Optional[str] = None,
    ):
        super().__init__(storage, bot)
        self.ai_provider = ai_provider
        self.message_handler = MessageHandler()
        self.max_tokens = max_tokens
        self.system_message = system_message
        self.conversation_log = ""

    def add_user_message(
        self, text: Optional[str] = None, ai_media: Optional[AIMediaBase] = None
    ):
        if ai_media:
            content = self.ai_provider.media_class(
                photo=ai_media.photo, mime_type=ai_media.mime_type
            ).render_content(text)
            self.message_handler.add_message("user", content)
        else:
            self.message_handler.add_message("user", text)
        self.conversation_log += f"user: {text if text else 'photo'}\n"

    def add_assistant_message(self, text: Optional[str] = None):
        self.message_handler.add_message("assistant", text)
        self.conversation_log += f"assistant: {text}\n"

    async def answer_with_ai(
        self,
        message: Message,
        sent_message: Message,
        notification: Optional[str] = None,
        apply_formatting: bool = True,
    ):
        if not self.message_handler.get_messages():
            await sent_message.edit_text(
                "🤖 Не знаю на що відповідати:)",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return

        logging.info(self.system_message + "\n\n" + self.conversation_log)

        final_text = await self._stream_response(
            sent_message, notification, apply_formatting
        )

        await sent_message.edit_text(
            f"{notification}\n\n{final_text}",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        logging.info(f"AI: {final_text}")
        await message.react(reaction=[ReactionTypeEmoji(emoji="👨‍💻")], is_big=True)
        return len(final_text.split())

    async def _stream_response(
        self, sent_message: Message, notification: Optional[str], apply_formatting: bool
    ) -> str:
        text = ""
        last_time = time.time()

        async for partial_text in self.ai_provider.generate_response(
            self.message_handler.get_messages(), self.max_tokens, self.system_message
        ):
            text += partial_text
            if time.time() - last_time > 5:
                cont_symbol = random.choice(["▌", "█"])
                formatted_text = telegram_format(text) if apply_formatting else text
                await sent_message.edit_text(
                    f"{notification}\n\n{formatted_text}{cont_symbol}",
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                last_time = time.time()

        return telegram_format(text) if apply_formatting else text
