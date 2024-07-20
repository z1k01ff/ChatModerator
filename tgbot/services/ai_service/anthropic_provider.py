import base64
from typing import AsyncGenerator, List, Optional
from anthropic import AsyncAnthropic, types as anthropic_types
from tgbot.services.ai_service.base_provider import AIMediaBase, AIProviderBase


class AnthropicMedia(AIMediaBase):
    def prepare_photo(self) -> str:
        return base64.b64encode(self.photo.getvalue()).decode("utf-8")

    def render_content(self, text: Optional[str] = None) -> list:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": self.mime_type,
                    "data": self.prepare_photo(),
                },
            },
        ]
        if text:
            content.append({"type": "text", "text": text})
        return content


class AnthropicProvider(AIProviderBase):
    def __init__(
        self, client: AsyncAnthropic, model_name: str = "claude-3-5-sonnet-20240620"
    ):
        super().__init__(media_class=AnthropicMedia)
        self.client = client
        self.model_name = model_name

    async def generate_response(
        self,
        messages: List[dict],
        max_tokens: int,
        system_message: Optional[str] = None,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        formatted_messages = [
            anthropic_types.MessageParam(role=msg["role"], content=msg["content"])
            for msg in messages
        ]
        async with self.client.messages.stream(
            max_tokens=max_tokens,
            model=self.model_name,
            messages=formatted_messages,
            system=system_message,
            temperature=temperature,
        ) as stream:
            async for partial_text in stream.text_stream:
                yield partial_text
