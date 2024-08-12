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


    async def analyze_and_update_context(self, user_id: int, user_full_name: str, message_text: str):
        current_context = self.user_contexts.get(user_id, f"{user_full_name} ({user_id}): No information available.")
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "update_user_context",
                    "description": "Update the context for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "new_context": {
                                "type": "string",
                                "description": "The new context for the user",
                            },
                        },
                        "required": ["new_context"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "do_nothing",
                    "description": "Do nothing when no update is needed",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
        ]

        messages = [
            {"role": "system", "content": "You are an AI assistant that maintains comprehensive user contexts."},
            {"role": "user", "content": f"""
Current context for {user_full_name} (ID: {user_id}):
{current_context}

New message:
{message_text}

Analyze this message and decide if the user's context needs updating. If yes, call update_user_context with a new, comprehensive context. If no update is needed, call do_nothing.

When updating the context, consider the following aspects of a user profile:
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
1. Keep it concise yet informative, aiming for 200-300 characters.
2. Use short phrases separated by semicolons.
3. Include the user's name and ID at the start.
4. Prioritize recent or recurring information.
5. Remove outdated or less relevant details.
6. Balance between stability (not changing too much) and capturing new insights.

Example format:
John Doe (123): 35yo software engineer; Python expert; AI enthusiast; informal communicator; daily user; seeking career growth; struggles with work-life balance; Linux user; fluent in English and Spanish; introverted; values continuous learning

Maintain similar comprehensiveness while adapting to the user's unique characteristics.
"""}
        ]

        logging.info(str(messages))
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
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
                    new_context = function_args.get("new_context")
                    self.update_user_context(user_id, new_context)
                    return f"Updated context for user {user_id}: {new_context}"
                elif function_name == "do_nothing":
                    return "No update needed"

        return "No action taken"