import base64
from enum import Enum
from io import BytesIO
from aiogram.types import Message
from anthropic import AsyncAnthropic
from runware import IImageInference, Runware
from tgbot.services.prompt_enhancer import ToolResponse, enhance_prompt


class ImageModel(str, Enum):
    FLUX_SCHNELL = "runware:100@1"
    FLUX_DEV = "runware:101@1"
    CIVITAI_618578 = "civitai:618578@693048"
    CIVITAI_81458 = "civitai:81458@132760"
    CIVITAI_101055 = "civitai:101055@128078"


async def prepare_seed_image(message: Message, seed_image) -> str | None:
    if seed_image:
        seed_image_binary: BytesIO = await message.bot.download(seed_image)
        seed_image_bytes = seed_image_binary.read()
        return base64.b64encode(seed_image_bytes).decode("utf-8")
    return None


async def generate_image(
    runware_client: Runware,
    positive_prompt: str,
    negative_prompt: str,
    seed_image_base64: str | None,
) -> str | None:
    request_image = IImageInference(
        positivePrompt=positive_prompt[:1500],
        negativePrompt=negative_prompt[:500] if negative_prompt else "",
        model=ImageModel.FLUX_SCHNELL,
        numberResults=1,
        useCache=False,
        height=1024,
        width=1024,
        steps=30,
        CFGScale=18,
        usePromptWeighting=True,
        seedImage=seed_image_base64,
    )
    images = await runware_client.imageInference(requestImage=request_image)
    return images[0].imageURL if images and images[0] and images[0].imageURL else None
