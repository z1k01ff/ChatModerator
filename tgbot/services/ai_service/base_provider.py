from io import BytesIO
from typing import AsyncGenerator, List, Optional, Type
from abc import ABC, abstractmethod


class AIMediaBase(ABC):
    def __init__(self, photo: BytesIO, mime_type: str = "image/jpeg"):
        self.photo = photo
        self.mime_type = mime_type

    @abstractmethod
    def prepare_photo(self) -> str:
        raise NotImplementedError("This method should be overridden by subclasses")

    @abstractmethod
    def render_content(self, text: Optional[str] = None) -> list:
        raise NotImplementedError("This method should be overridden by subclasses")


class AIProviderBase(ABC):
    def __init__(self, media_class: Type[AIMediaBase]):
        self.media_class = media_class

    @abstractmethod
    async def generate_response(
        self,
        messages: List[dict],
        max_tokens: int,
        system_message: Optional[str] = None,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("This method should be overridden by subclasses")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(media_class={self.media_class.__name__})"