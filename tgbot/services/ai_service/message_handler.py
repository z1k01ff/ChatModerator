from typing import List, Literal


class MessageHandler:
    def __init__(self, messages: List | None = None):
        self.messages = messages or []
        self.photos: int = 0

    def add_message(self, role: Literal["user", "assistant"], content):
        self.messages.append({"role": role, "content": content})
        if isinstance(content, dict) and content.get("type") == "image_url":
            self.photos += 1

    def get_messages(self):
        return self.messages
