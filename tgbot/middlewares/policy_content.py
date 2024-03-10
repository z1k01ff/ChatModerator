from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from openai import AsyncOpenAI

from tgbot.services.rating import change_rating


class OpenAIModerationMiddleware(BaseMiddleware):
    warning_messages = {
        "hate": "Увага: Ваше повідомлення містить елементи ненависті. Будь ласка, утримайтеся від таких висловлювань.\n\n⚠️Ваш соціальний рейтинг був знижений на 1.",
        "hate/threatening": "Увага: Ваше повідомлення містить погрози та домагання. Не допускайте такої поведінки.\n\n⚠️Ваш соціальний рейтинг був знижений на 1.",
        "violence/graphic": "Увага: Ваше повідомлення містить ознаки насильства. Такі повідомлення неприпустимі.\n\n⚠️Ваш соціальний рейтинг був знижений на 1.",
        "harassment/threatening": "Увага: Ваше повідомлення містить погрози та домагання. Не допускайте такої поведінки.\n\n⚠️Ваш соціальний рейтинг був знижений на 1.",
        "violence": "Увага: Ваше повідомлення містить насильство. Будь ласка, дотримуйтеся правил спільноти.\n\n⚠️Ваш соціальний рейтинг був знижений на 1.",
    }

    def __init__(self, openai_client: AsyncOpenAI):
        super().__init__()
        self.client = openai_client
        self.warned_users = dict()

    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, types.Message) or not event.text:
            return await handler(event, data)
        if event.forward_from_chat or event.forward_from:
            return await handler(event, data)

        response = await self.client.moderations.create(input=event.text)
        user_id = event.from_user.id
        for category, flagged in response.results[0].categories.model_dump().items():
            if flagged:
                text = self.warning_messages.get(category)
                if text:
                    if user_id not in self.warned_users:
                        self.warned_users[user_id] = {
                            "category": category,
                            "times": 1,
                        }
                    else:
                        self.warned_users[user_id]["times"] += 1
                    times_violated = self.warned_users[user_id]["times"]

                    if times_violated == 1:
                        await event.reply(text)
                    elif times_violated == 3:
                        await event.reply(
                            "Увага: Ви продовжуєте токсично себе поводити. \n\n⚠️Ваш соціальний рейтинг був знижений на 3."
                        )
                        await change_rating(user_id, -2, data["repo"])

                    elif self.warned_users[user_id]["times"] > 4:
                        await event.reply(
                            "За неодноразове порушення правил. \n\n⚠️Ваш рейтинг був знижений на 5."
                        )
                        await change_rating(user_id, -5, data["repo"])
                        # clear the user from the dict
                        del self.warned_users[user_id]

                    break  # Stop after sending the first relevant warning

        return await handler(event, data)
