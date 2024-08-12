import logging
from openai import AsyncOpenAI
import json
from typing import Dict, Callable
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
                    "description": "Update the context for a specific user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "The ID of the user whose context is being updated",
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
            {"role": "system", "content": "You are an AI assistant that maintains concise user contexts."},
            {"role": "user", "content": f"""
Current context for {user_full_name} (ID: {user_id}):
{current_context}

New message:
{message_text}

Analyze this message and decide if the user's context needs updating. If yes, call update_user_context with a new, concise context (max 30 phrases). If no update is needed, call do_nothing.
Try not to rewrite the context completely, more adding if possible.

Rules for context updates:
1. Keep it under 150 characters.
2. Focus on key traits, interests, or behaviors.
3. Use short phrases separated by semicolons.
4. Include the user's name and ID at the start.
5. Prioritize recent or recurring information.
6. Remove outdated or less relevant details.

Example format:
John Doe (123): Python dev; coffee lover; frequent joke teller; interested in AI; ...

Other users' contexts:
{json.dumps({k: v for k, v in self.user_contexts.items() if k != user_id}, indent=2)}

Maintain similar conciseness for all users.
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
            available_functions: Dict[str, Callable] = {
                "update_user_context": self.update_user_context,
                "do_nothing": self.do_nothing,
            }

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)

                if function_name == "update_user_context":
                    function_to_call(
                        user_id=function_args.get("user_id"),
                        new_context=function_args.get("new_context"),
                    )
                    return f"Updated context for user {user_id}: {function_args.get('new_context')}"
                elif function_name == "do_nothing":
                    function_to_call()
                    return "No update needed"

        return "No action taken"