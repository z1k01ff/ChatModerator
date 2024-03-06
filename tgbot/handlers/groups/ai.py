import logging
from io import BytesIO

from aiogram import Bot, F, Router, flags, types
from aiogram.filters import Command, or_f
from anthropic import AsyncAnthropic

from tgbot.services.ai_answers import AIConversation, AIMedia

ai_router = Router()
ai_router.message.filter(F.chat.id == -1001415356906)


@ai_router.message(Command("ai", magic=F.args.as_("prompt")))
@ai_router.message(Command("ai", magic=F.args.as_("prompt")), F.photo[-1].as_("photo"))
@ai_router.message(
    F.reply_to_message.from_user.id == 827638584,
    F.reply_to_message.text.as_("assistant_message"),
    or_f(F.text.as_("prompt"), F.caption.as_("prompt")),
)
@flags.rate_limit(limit=300, key="ai", max_times=3)
@flags.override(user_id=362089194)
async def ask_ai(
    message: types.Message,
    prompt: str,
    anthropic_client: AsyncAnthropic,
    bot: Bot,
    photo: types.PhotoSize | None = None,
    assistant_message: str | None = None,
):
    reply_prompt = None
    if reply := message.reply_to_message:
        if reply.text:
            reply_prompt = reply.text
        elif reply.caption:
            reply_prompt = reply.caption

    if message.quote:
        reply_prompt = message.quote.text

    reply_photo = (
        message.reply_to_message.photo[-1]
        if message.reply_to_message and message.reply_to_message.photo
        else None
    )

    ai_conversation = AIConversation(
        system_message=f"""You're funny average Ukrainian Stepan Bandera enjoyer, and not helpful assistant at all. 
You always troll people and make fun of them. Speak Ukrainian by default.
You are in {message.chat.title} Telegram Group.

The current person you are talking to is {message.from_user.full_name} and he is a member of the group.
"""
    )

    if assistant_message:
        logging.info("Answering to assistant message")
        if message.quote:
            prompt = f"You previously said: {message.quote} {prompt}"
        else:
            prompt = f"You previously said: {assistant_message} {prompt}"

    if reply_prompt or reply_photo:
        if reply_photo:
            logging.info("Adding reply message with photo")
            photo_bytes_io = await bot.download(
                reply_photo, destination=BytesIO()  # type: ignore
            )
            ai_media = AIMedia(photo_bytes_io)
            ai_conversation.add_user_message(text=reply_prompt, ai_media=ai_media)
        else:
            logging.info("Adding reply message without photo")
            ai_conversation.add_user_message(text=reply_prompt)
        ai_conversation.add_assistant_message(
            "So, that's the context. Now, let's continue."
        )

    if photo:
        logging.info("Adding user message with photo")
        photo_bytes_io = await bot.download(photo, destination=BytesIO())
        ai_media = AIMedia(photo_bytes_io)
        ai_conversation.add_user_message(text=prompt, ai_media=ai_media)
    else:
        logging.info("Adding user message without photo")
        ai_conversation.add_user_message(text=prompt)

    await ai_conversation.answer_with_ai(message, anthropic_client)
