import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.utils.markdown import hitalic
from aiogram.types import Message
from runware import Runware
from anthropic import AsyncAnthropic
from tgbot.services.image_generator import generate_image, prepare_seed_image
from tgbot.services.prompt_enhancer import enhance_prompt, ToolResponse

ai_image_router = Router()

@ai_image_router.message(Command("img", magic=F.args.as_("prompt")))
@ai_image_router.message(Command("img"), F.reply_to_message.text.as_("prompt"))
async def handle_generate_image(
    message: Message,
    runware_client: Runware,
    anthropic_client: AsyncAnthropic,
    prompt: str,
):
    seed_image = message.reply_to_message.photo[-1] if message.reply_to_message and message.reply_to_message.photo else None
    sent_message = await message.reply("🖼 Обробка запиту, будь ласка, зачекайте...")

    try:
        # Step 1: Enhance the prompt
        enhanced_prompt_data: ToolResponse = await enhance_prompt(anthropic_client, prompt)
        positive_prompt = enhanced_prompt_data.positive_prompt if not enhanced_prompt_data.refused else prompt
        negative_prompt = enhanced_prompt_data.negative_prompt if not enhanced_prompt_data.refused else ""

        # Update the message with the enhanced prompt
        caption = f"🔍 Оригінальний запит: {prompt}\n\n"
        if not enhanced_prompt_data.refused:
            caption += f"✨ Покращений запит: {positive_prompt}\n\n"
            caption += f"🚫 Негативний запит: {negative_prompt}\n\n"
        if seed_image:
            caption += "\n\n🖼 Використано вхідне зображення"
        formatted_caption = "<blockquote expandable>" + hitalic(caption.strip()) + "</blockquote>"
        await sent_message.edit_text(formatted_caption)

        # Step 2: Generate the image
        seed_image_base64 = await prepare_seed_image(message, seed_image)
        image_url = await generate_image(runware_client, positive_prompt, negative_prompt, seed_image_base64)

        if not image_url:
            return await sent_message.edit_text("❌ Не вдалося згенерувати зображення. Спробуйте ще раз.")

        await message.reply_photo(photo=image_url, caption=None, has_spoiler=True)

    except Exception as e:
        logging.error(f"Error generating image: {e}")
        await sent_message.edit_text(f"<blockquote>Сталася помилка під час генерації зображення: {str(e)}</blockquote>")
