import base64
from enum import Enum
from io import BytesIO
import logging
from aiogram.types import Message
from runware import IImageInference, Runware
from PIL import Image
from pydantic import BaseModel


class ImageModel(str, Enum):
    FLUX_SCHNELL = "runware:100@1"
    FLUX_DEV = "runware:101@1"
    CIVITAI_618578 = "civitai:618578@693048"
    CIVITAI_81458 = "civitai:81458@132760"
    CIVITAI_101055 = "civitai:101055@128078"


class SeedImage(BaseModel):
    base64_image: str
    width: int
    height: int


async def prepare_seed_image(message: Message, seed_image) -> SeedImage | None:
    if not seed_image:
        return None

    seed_image_bytes = await download_seed_image(message, seed_image)
    width, height, cropped_image = calculate_new_size(seed_image_bytes)

    return SeedImage(
        base64_image=base64.b64encode(cropped_image).decode("utf-8"),
        width=width,
        height=height,
    )


async def download_seed_image(message: Message, seed_image) -> bytes:
    seed_image_binary: BytesIO = await message.bot.download(seed_image)
    return seed_image_binary.read()


def calculate_new_size(seed_image_bytes: bytes) -> tuple[int, int, bytes]:
    with Image.open(BytesIO(seed_image_bytes)) as img:
        original_width, original_height = img.size

        # Calculate the aspect ratio
        aspect_ratio = original_width / original_height

        # Define the target dimensions
        min_dim = 512
        max_dim = 2048
        step = 64

        # Calculate new dimensions
        if aspect_ratio > 1:  # Width is larger
            new_width = min(
                max_dim, max(min_dim, original_width - (original_width % step))
            )
            new_height = int(new_width / aspect_ratio)
            new_height = min(max_dim, max(min_dim, new_height - (new_height % step)))
        else:  # Height is larger or equal
            new_height = min(
                max_dim, max(min_dim, original_height - (original_height % step))
            )
            new_width = int(new_height * aspect_ratio)
            new_width = min(max_dim, max(min_dim, new_width - (new_width % step)))

        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # If the image is still too large, crop it
        if new_width > max_dim or new_height > max_dim:
            left = (new_width - max_dim) // 2 if new_width > max_dim else 0
            top = (new_height - max_dim) // 2 if new_height > max_dim else 0
            right = left + min(new_width, max_dim)
            bottom = top + min(new_height, max_dim)
            img_resized = img_resized.crop((left, top, right, bottom))

        # Convert the image to bytes
        img_byte_arr = BytesIO()
        img_resized.save(img_byte_arr, format=img.format)
        img_byte_arr = img_byte_arr.getvalue()

        return img_resized.width, img_resized.height, img_byte_arr


async def generate_image(
    runware_client: Runware,
    positive_prompt: str,
    negative_prompt: str,
    seed_image: SeedImage | None,
) -> str | None:
    logging.info(f"Generating image {seed_image}")
    request_image = IImageInference(
        positivePrompt=positive_prompt[:1500],
        negativePrompt=negative_prompt[:500] if negative_prompt else "",
        model=ImageModel.FLUX_SCHNELL,
        numberResults=1,
        useCache=False,
        height=seed_image.height if seed_image else 1024,
        width=seed_image.width if seed_image else 1024,
        steps=30,
        CFGScale=18,
        usePromptWeighting=True,
        seedImage=seed_image.base64_image if seed_image else None,
    )
    images = await runware_client.imageInference(requestImage=request_image)
    return images[0].imageURL if images and images[0] and images[0].imageURL else None
