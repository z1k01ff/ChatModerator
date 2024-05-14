from typing import List, Literal


class MessageHandler:
    def __init__(self, messages: List | None = None):
        self.messages = messages or []

    def add_message(self, role: Literal["user", "assistant"], content):
        self.messages.append({"role": role, "content": content})

    def get_messages(self):
        return self.messages
