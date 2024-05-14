import base64
from typing import AsyncGenerator, List, Optional

from openai import AsyncOpenAI

from tgbot.services.ai_service.base_provider import AIMediaBase, AIProviderBase


class OpenAIMedia(AIMediaBase):
    def prepare_photo(self) -> str:
        return base64.b64encode(self.photo.getvalue()).decode("utf-8")

    def render_content(self, text: Optional[str] = None) -> list:
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{self.mime_type};base64,{self.prepare_photo()}"
                },
            },
        ]
        if text:
            content.insert(0, {"type": "text", "text": text})
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
    ) -> AsyncGenerator[str, None]:
        if system_message:
            messages.insert(0, {"role": "system", "content": system_message})

        chat_completion = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
        )

        async for chunk in chat_completion:
            if chunk.choices and chunk.choices[0].delta:
                yield chunk.choices[0].delta.content or ""
