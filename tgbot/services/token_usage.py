import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage


@dataclass
class ModelPricing:
    input_price: float  # Price per million tokens (MTok) for input
    output_price: float  # Price per million tokens (MTok) for output


# Define pricing for different models
Haiku = ModelPricing(input_price=0.25, output_price=1.25)
Sonnet = ModelPricing(input_price=3, output_price=15)
Opus = ModelPricing(input_price=15, output_price=75)


class TokenUsageManager:
    def __init__(self, storage: RedisStorage, bot: Bot):
        self.storage = storage
        self.bot = bot

    async def get_usage(self, group_id: int, user_id: int) -> dict:
        key = f"{group_id}_{user_id}"
        storage_key = StorageKey(self.bot.id, group_id, group_id)

        # Attempt to retrieve group data from storage
        group_state: dict = await self.storage.get_data(storage_key)

        # Return usage data if present, else default to 0 for both input and output
        return group_state.get(key, {"input": 0, "output": 0})

    async def update_usage(
        self,
        group_id: int,
        user_id: int,
        input_usage_delta: int,
        output_usage_delta: int,
    ):
        key = f"{group_id}_{user_id}"
        storage_key = StorageKey(self.bot.id, group_id, group_id)

        # Retrieve current state or initialize if absent
        group_state: dict = await self.storage.get_data(storage_key)
        user_usage = group_state.get(key, {"input": 0, "output": 0})

        # Update usage data with new deltas
        user_usage["input"] += input_usage_delta
        user_usage["output"] += output_usage_delta
        group_state[key] = user_usage

        logging.info(
            f'User {user_id} usage updated: {user_usage["input"]} input, {user_usage["output"]} output'
        )
        # Save updated state back to storage
        await self.storage.set_data(storage_key, group_state)

    async def calculate_cost(
        self, model_pricing: ModelPricing, group_id: int, user_id: int
    ) -> float:
        usage = await self.get_usage(group_id, user_id)

        logging.info(
            f"Calculating cost for user {user_id} with {usage['input']} input and {usage['output']} output"
        )
        # Calculate total cost based on model pricing and accumulated usage
        total_cost = (
            model_pricing.input_price * usage["input"]
            + model_pricing.output_price * usage["output"]
        ) / 1_000_000
        return round(total_cost, 2)

    async def reset_usage(self, group_id: int, user_id: int):
        key = f"{group_id}_{user_id}"
        storage_key = StorageKey(self.bot.id, group_id, group_id)

        # Retrieve current state or initialize if absent
        group_state: dict = await self.storage.get_data(storage_key)
        group_state[key] = {"input": 0, "output": 0}

        # Save updated state back to storage
        await self.storage.set_data(storage_key, group_state)
        logging.info(f"User {user_id} usage reset")
