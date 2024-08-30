import logging
from openai import AsyncOpenAI
import json
from typing import Dict
from aiogram.fsm.context import FSMContext

class AIUserContextManager:
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai_client = openai_client
        self.user_contexts: Dict[int, str] = {}

    async def load_contexts(self, state: FSMContext):
        data = await state.get_data()
        if 'user_contexts' in data:
            self.user_contexts = json.loads(data['user_contexts'])

    async def save_contexts(self, state: FSMContext):
        await state.update_data(user_contexts=json.dumps(self.user_contexts))

    def update_user_context(self, user_id: int, new_context: str):
        self.user_contexts[user_id] = new_context

    def do_nothing(self):
        pass

    def get_all_contexts(self) -> str:
        contexts = []
        for user_id, context in self.user_contexts.items():
            contexts.append(f"{context}")
        return "\n".join(contexts)

    async def update_contexts_from_history(self, chat_history: str):
        await self.analyze_and_update_context(chat_history)

    async def analyze_and_update_context(self, chat_history: str):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "update_user_context",
                    "description": "Update the context for each user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "The ID of the user",
                            },
                            "new_context": {
                                "type": "string",
                                "description": "The new context for the user",
                            },
                        },
                        "required": ["user_id", "new_context"],
                    },
                },
            },
        ]

        messages = [
            {"role": "system", "content": "You are an AI assistant that maintains comprehensive user contexts."},
            {"role": "user", "content": f"""
Analyze the following chat history and update the contexts for all users mentioned:

{chat_history}

For each user that appears in the chat history, create or update their context. Consider the following aspects:

1. Demographics: Age, gender, location, occupation, education level
2. Interests and Hobbies: Both general and specific areas of interest
3. Skills and Expertise: Professional and personal competencies
4. Communication Style: Formal/informal, verbose/concise, use of emojis/slang
5. Behavioral Patterns: Frequency of interaction, types of queries/requests
6. Preferences: Likes, dislikes, preferred topics or interaction styles
7. Goals and Motivations: Short-term and long-term objectives
8. Pain Points or Challenges: Issues the user frequently encounters or asks about
9. Technology Usage: Devices, platforms, or software they commonly use
10. Language Proficiency: Native language, other languages spoken
11. Cultural Background: Relevant cultural influences or references
12. Relationship Status: Single, married, family situation if relevant
13. Personality Traits: Extrovert/introvert, analytical/creative, etc.
14. Values and Beliefs: Important principles or ideologies they adhere to
15. Recent Life Events: Significant occurrences that might affect their context

Rules for context updates:
1. Keep it concise yet informative, aiming for 200-300 characters per user.
2. Use short phrases separated by semicolons.
3. Include the user's name and ID at the start.
4. Prioritize recent or recurring information.
5. Remove outdated or less relevant details.
6. Balance between stability (not changing too much) and capturing new insights.

Example format:
John Doe (123): 35yo software engineer; Python expert; AI enthusiast; informal communicator; daily user; seeking career growth; struggles with work-life balance; Linux user; fluent in English and Spanish; introverted; values continuous learning

Call the update_user_context function for each user that needs their context updated or created.
"""}
        ]

        logging.info(str(messages))
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                if function_name == "update_user_context":
                    user_id = function_args.get("user_id")
                    new_context = function_args.get("new_context")
                    self.update_user_context(user_id, new_context)
                    logging.info(f"Updated context for user {user_id}: {new_context}")

        return "Context update completed"
