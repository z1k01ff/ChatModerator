import datetime
import logging
from typing import Dict, Any, Callable, Awaitable

from aiogram import types, BaseMiddleware
from openai import AsyncOpenAI


class OpenAIModerationMiddleware(BaseMiddleware):
    warning_messages = {
        "hate": "Увага: Ваше повідомлення містить елементи ненависті. Будь ласка, утримайтеся від таких висловлювань. Якщо будете продовжувати, Вас можуть заблокувати",
        "hate/threatening": "Увага: Ваше повідомлення містить погрози та домагання. Не допускайте такої поведінки. Якщо будете продовжувати, Вас можуть заблокувати",
        "violence/graphic": "Увага: Ваше повідомлення містить ознаки насильства. Такі повідомлення неприпустимі. Якщо будете продовжувати, Вас можуть заблокувати.",
        "harassment/threatening": "Увага: Ваше повідомлення містить погрози та домагання. Не допускайте такої поведінки. Якщо будете продовжувати, Вас можуть заблокувати",
        "violence": "Увага: Ваше повідомлення містить насильство. Будь ласка, дотримуйтеся правил спільноти. Якщо будете продовжувати, Вас можуть заблокувати",
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

        response = await self.client.moderations.create(input=event.text)
        user_id = event.from_user.id
        for category, flagged in response.results[0].categories.model_dump().items():
            logging.info(f"Category {category} flagged: {flagged}")
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
                        await event.reply("Увага: Ви продовжуєте порушувати правила спільноти. Якщо будете продовжувати, Вас можуть заблокувати")

                    elif self.warned_users[user_id]["times"] > 4:
                        await event.chat.restrict(user_id, permissions=types.ChatPermissions(can_send_messages=False), until_date=datetime.timedelta(hours=1))
                        await event.reply("Ви були заблоковані за порушення правил спільноти на 1 годину")

                    break  # Stop after sending the first relevant warning

        return await handler(event, data)
