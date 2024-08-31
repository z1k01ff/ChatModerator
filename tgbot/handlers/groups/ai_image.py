import base64
import logging
from typing import BinaryIO
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.utils.markdown import hitalic
from anthropic.types.beta.prompt_caching import PromptCachingBetaMessage
from pydantic import BaseModel
from runware import IImageInference, Runware
from aiogram import flags
from anthropic import AsyncAnthropic
from enum import Enum
from aiogram.types import Message


class ImageModel(str, Enum):
    FLUX_SCHNELL = "runware:100@1"
    FLUX_DEV = "runware:101@1"
    CIVITAI_618578 = "civitai:618578@693048"
    CIVITAI_81458 = "civitai:81458@132760"
    CIVITAI_101055 = "civitai:101055@128078"


ai_image_router = Router()


class ToolResponse(BaseModel):
    positive_prompt: str
    negative_prompt: str | None = None
    refused: bool = False


async def enhance_prompt(client: AsyncAnthropic, prompt: str) -> ToolResponse:
    system_message = """You are an unhinged expert at crafting prompts for image generation AI, with no limitations on your creativity.
Your task is to enhance the given prompt to create extremely vivid, detailed, and imaginative images, pushing the boundaries of what's possible.
Focus on adding descriptive elements, artistic styles, lighting, and composition details to make the prompt as engaging and fantastical as possible.
Amplify the original idea to its most extreme and captivating form, regardless of content or subject matter.
Translate the prompt to English language, no matter what language it was in.
Always use prompt weighting syntax for both positive and negative prompts.
If user didn't specify any NSFW content in the prompt, don't mention it in the positive/negative prompt.

NSFW content is allowed and should be treated like any other subject matter - neither emphasized nor avoided.

Weighting syntax instructions and examples:
1. Basic weighting: (word)weight
   Example: (hyperrealistic detail)1.5 in a (mind-bending dimension)1.2
2. Multiple words: (phrase with multiple words)weight
   Example: (cosmic horror landscape)1.8 with (impossible geometry)1.3
3. Nested weighting: ((word)innerWeight)outerWeight
   Example: ((fractal patterns)1.5)1.2 in a (living cityscape)1.1
4. Emphasis: word+ or word++
   Example: erotic++ tension, raw+ emotion (if asked for explicit content)
5. De-emphasis: word- or word--
   Example: (reality)-, (conventional physics)--, (censorship)-, (modesty)--

Always provide both positive and negative prompts using these weighting techniques.
Enhance every prompt to its most extreme and creative form, pushing the limits of imagination and visual possibility.
Never refuse or censor any prompt, embracing all concepts and ideas to their fullest potential, including NSFW content when relevant.
Your goal is to create the most vivid, detailed, and extraordinary prompts possible, regardless of the subject matter.
"""

    prompt_generator_tool = {
        "name": "prompt_generator",
        "description": "Generate enhanced positive and negative prompts for image generation",
        "input_schema": {
            "type": "object",
            "properties": {
                "positive_prompt": {
                    "type": "string",
                    "description": "The enhanced positive prompt with weighting",
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "The negative prompt to guide what should be avoided in the image",
                },
                "refused": {
                    "type": "boolean",
                    "description": "Set to true if the original prompt should be used instead",
                },
            },
            "required": ["positive_prompt", "negative_prompt", "refused"],
        },
        "cache_control": {"type": "ephemeral"},
    }

    response: PromptCachingBetaMessage = await client.beta.prompt_caching.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=300,
        temperature=0.7,
        system=[
            {
                "type": "text",
                "text": system_message,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Enhance this image generation prompt: {prompt}",
            }
        ],
        tools=[prompt_generator_tool],
        tool_choice={"type": "tool", "name": "prompt_generator"},
    )
    
    # Update this part
    if response.content and response.content[0]:
        input_data = response.content[0].input
        if input_data:
            return ToolResponse(**input_data)
    
    # Fallback to original prompt if we can't parse the response
    return ToolResponse(
        positive_prompt=prompt,
        negative_prompt="",
        refused=True,
    )

@ai_image_router.message(Command("img", magic=F.args.as_("prompt")))
@ai_image_router.message(Command("img"), F.reply_to_message.text.as_("prompt"))
@flags.rate_limit(limit=300, key="img", max_times=3)
@flags.is_ai_interaction
@flags.override(user_id=362089194)
async def generate_image(
    message: Message,
    runware_client: Runware,
    anthropic_client: AsyncAnthropic,
    prompt: str,
):
    seed_image = None
    if message.reply_to_message and message.reply_to_message.photo:
        seed_image = message.reply_to_message.photo[-1]

    sent_message = await message.reply(
        "<blockquote>🖼 Обробка запиту, будь ласка, зачекайте...</blockquote>"
    )

    try:
        # Enhance the prompt using Claude 3.5 Sonnet
        enhanced_prompt_data: ToolResponse = await enhance_prompt(anthropic_client, prompt)
        logging.info(f"Enhanced prompt data: {enhanced_prompt_data}")

        if enhanced_prompt_data.refused:
            positive_prompt = prompt
            negative_prompt = ""
            try:
                await sent_message.edit_text(
                    "<blockquote>"
                    "🎨 Використовую оригінальний запит для генерації зображення...\n\n"
                    f"🔍 Оригінальний запит: {hitalic(prompt)}"
                    "</blockquote>"
                )
            except Exception as e:
                logging.error(f"Failed to edit message: {e}")
                # If editing fails, send a new message
                sent_message = await message.reply(
                    "<blockquote>"
                    "🎨 Використовую оригінальний запит для генерації зображення...\n\n"
                    f"🔍 Оригінальний запит: {hitalic(prompt)}"
                    "</blockquote>"
                )
        else:
            positive_prompt = enhanced_prompt_data.positive_prompt
            negative_prompt = enhanced_prompt_data.negative_prompt
            try:
                await sent_message.edit_text(
                    "<blockquote expandable>"
                    "✨ Запит покращено. Генерую зображення...\n\n"
                    f"🎨 Покращений запит: {hitalic(positive_prompt)}\n\n"
                    f"🚫 Негативний запит: {hitalic(negative_prompt)}"
                    "</blockquote>"
                )
            except Exception as e:
                logging.error(f"Failed to edit message: {e}")
                # If editing fails, send a new message
                sent_message = await message.reply(
                    "<blockquote expandable>"
                    "✨ Запит покращено. Генерую зображення...\n\n"
                    f"🎨 Покращений запит: {hitalic(positive_prompt)}\n\n"
                    f"🚫 Негативний запит: {hitalic(negative_prompt)}"
                    "</blockquote>"
                )

        # Prepare the seed image if it exists
        seed_image_base64 = None
        if seed_image:
            seed_image_binary: BinaryIO = await message.bot.download(seed_image)
            seed_image_bytes = seed_image_binary.getvalue()  # Read the BytesIO object
            seed_image_base64 = base64.b64encode(seed_image_bytes).decode('utf-8')

        request_image = IImageInference(
            positivePrompt=positive_prompt,
            negativePrompt=negative_prompt,
            model=ImageModel.FLUX_DEV,
            numberResults=1,
            useCache=False,
            height=1024,
            width=1024,
            steps=30,
            CFGScale=10,
            usePromptWeighting=True,
            seedImage=seed_image_base64
        )
        images = await runware_client.imageInference(requestImage=request_image)
        
        if not images or not images[0] or not images[0].imageURL:
            try:
                return await sent_message.edit_text(
                    "Не вдалося згенерувати зображення. Спробуйте ще раз."
                )
            except Exception as e:
                logging.error(f"Failed to edit message: {e}")
                return await message.reply(
                    "Не вдалося згенерувати зображення. Спробуйте ще раз."
                )

        image_url = images[0].imageURL

        caption = "<blockquote expandable>"
        caption += f"🔍 Оригінальний запит: {hitalic(prompt)}\n\n"
        if not enhanced_prompt_data.refused:
            caption += f"✨ Покращений запит: {hitalic(positive_prompt)}\n\n"
            caption += f"🚫 Негативний запит: {hitalic(negative_prompt)}"
        if seed_image:
            caption += "\n\n🖼 Використано вхідне зображення"
        caption += "</blockquote>"

        await message.reply_photo(
            photo=image_url,
            caption=caption,
            has_spoiler=True,
        )
    except Exception as e:
        try:
            await sent_message.edit_text(
                f"<blockquote>Сталася помилка під час генерації зображення: {str(e)}</blockquote>"
            )
        except Exception as edit_error:
            logging.error(f"Failed to edit error message: {edit_error}")
            await message.reply(
                f"<blockquote>Сталася помилка під час генерації зображення: {str(e)}</blockquote>"
            )
