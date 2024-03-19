from datetime import datetime, timedelta

from infrastructure.database.repo.requests import RequestsRepo
from aiogram.types import (
    MessageReactionUpdated,
    ReactionTypeEmoji,
)
from enum import Enum, auto


RATING_CACHE_TTL = timedelta(minutes=3)
POSITIVE_EMOJIS = {"👍", "❤", "🔥", "❤‍🔥", "😁", "🤣"}
NEGATIVE_EMOJIS = {"👎", "🤡", "💩"}


class InterationType(Enum):
    POSITIVE = auto()
    NEGATIVE = auto()


class UserRank(Enum):
    PIG_HERDER = auto()
    COSSACK = auto()
    OTAMAN = auto()
    HETMAN = auto()
    SORCERER = auto()
    KING = auto()

    @classmethod
    def from_rating(cls, rating: int):
        if rating >= 1000:
            return cls.KING
        elif 600 <= rating < 1000:
            return cls.SORCERER
        elif 300 <= rating < 600:
            return cls.HETMAN
        elif 100 <= rating < 300:
            return cls.OTAMAN
        elif 50 <= rating < 100:
            return cls.COSSACK
        else:
            return cls.PIG_HERDER


def get_reaction_change(
    old_reaction: list[ReactionTypeEmoji],
    new_reaction: list[ReactionTypeEmoji],
):
    # Convert reactions to sets for easier comparison
    old_set = set([reaction.emoji for reaction in old_reaction])
    new_set = set([reaction.emoji for reaction in new_reaction])

    # Determine the difference
    added = new_set - old_set

    # Check if the change is positive or negative
    for emoji in added:
        if emoji in POSITIVE_EMOJIS:
            return InterationType.POSITIVE
        elif emoji in NEGATIVE_EMOJIS:
            return InterationType.NEGATIVE


def is_rating_cached(helper_id: int, user_id: int, ratings_cache: dict) -> bool:
    key = (helper_id, user_id)
    now = datetime.now()

    if key in ratings_cache:
        # Check if the cache entry is still valid (e.g., within 1 minute)
        if now - ratings_cache[key] < RATING_CACHE_TTL:
            return True  # It's a duplicate within the time window

    # Update the cache
    ratings_cache[key] = now
    return False


async def change_rating(
    helper_id: int, change: int, repo: RequestsRepo
) -> tuple[int, int]:
    current_rating = await repo.rating_users.get_rating_by_user_id(helper_id)
    if current_rating is None:
        await repo.rating_users.add_user_for_rating(helper_id, change)
        return 0, change

    # Update the rating
    new_rating = current_rating + change
    await repo.rating_users.update_rating_by_user_id(helper_id, new_rating)

    return current_rating, new_rating


def calculate_rating_change(
    actor_rank: UserRank,
    target_rank: UserRank,
    interaction_type: InterationType | None = None,
) -> int:
    if not interaction_type:
        return 0
    scale = 2
    exponent = 2

    rank_diff = abs(actor_rank.value - target_rank.value)
    scale_factor = ((actor_rank.value / 6) ** exponent) * rank_diff * scale
    delta_rating = max(1, min(10, round(scale_factor)))

    if interaction_type == InterationType.NEGATIVE:
        delta_rating *= -1

    return delta_rating


async def reaction_rating_calculator(
    reaction: MessageReactionUpdated, repo: RequestsRepo, helper_id, actor_id
) -> int:
    helper_rating = await repo.rating_users.get_rating_by_user_id(helper_id) or 0
    actor_rating = await repo.rating_users.get_rating_by_user_id(actor_id) or 0

    helper_rank = UserRank.from_rating(helper_rating)
    actor_rank = UserRank.from_rating(actor_rating)

    reaction_change = get_reaction_change(reaction.old_reaction, reaction.new_reaction)
    rating_change = calculate_rating_change(actor_rank, helper_rank, reaction_change)

    return rating_change
