import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.markdown import hcode
from runware import IImageInference, Runware
from aiogram import flags
from anthropic import AsyncAnthropic
from enum import Enum

class ImageModel(str,Enum):
    FLUX_SCHNELL = "runware:100@1"
    FLUX_DEV = "runware:101@1"
    CIVITAI_618578 = "civitai:618578@693048"
    CIVITAI_81458 = "civitai:81458@132760"
    CIVITAI_101055 = "civitai:101055@128078"

ai_image_router = Router()

async def enhance_prompt(client: AsyncAnthropic, prompt: str) -> str:
    system_message = """You are an expert at crafting prompts for image generation AI. 
Your task is to enhance the given prompt to create more vivid, detailed, and creative images. 
Focus on adding descriptive elements, artistic styles, lighting, and composition details. 
Keep the enhanced prompt concise and relevant to the original idea as close as 80%.
Include only one prompt in the response, no comments.
Translate the prompt to English language, no matter what language it was in.
"""

    response = await client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=150,
        temperature=0.7,
        system=system_message,
        messages=[
            {"role": "user", "content": f"Enhance this image generation prompt: {prompt}"}
        ]
    )
    
    return response.content[0].text

@ai_image_router.message(Command("img", magic=F.args.as_("prompt")))
@flags.rate_limit(limit=300, key="img", max_times=3)
@flags.is_ai_interaction
@flags.override(user_id=362089194)
async def generate_image(
    message: types.Message, 
    runware_client: Runware, 
    anthropic_client: AsyncAnthropic,
    prompt: str
):
    sent_message = await message.reply("🖼 Обробка запиту та генерація зображення, будь ласка, зачекайте...")

    try:
        # Enhance the prompt using Claude 3.5 Sonnet
        enhanced_prompt = await enhance_prompt(anthropic_client, prompt)
        logging.info(f"Enhanced prompt: {enhanced_prompt}")

        request_image = IImageInference(
            positivePrompt=enhanced_prompt,
            model=ImageModel.FLUX_DEV,
            numberResults=1,
            useCache=False,
            height=1024,
            width=1024,
            steps=30,
            CFGScale=10,    
        )
        images = await runware_client.imageInference(requestImage=request_image)
        await sent_message.delete()
        if not images:
            return await message.reply(
                "Не вдалося згенерувати зображення. Спробуйте ще раз."
            )

        image_url = images[0].imageURL
        # nsfw_content = images[0].NSFWContent

        if not image_url:
            return await message.reply(
                "Не вдалося згенерувати зображення. Спробуйте ще раз."
            )

        await message.reply_photo(
            photo=image_url,
            caption=f"<blockquote expandable>{hcode(enhanced_prompt)}</blockquote>",
            has_spoiler=True,
        )
    except Exception as e:
        await message.reply(f"An error occurred while generating the image: {str(e)}")
