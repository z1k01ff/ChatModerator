from datetime import datetime, timedelta

from infrastructure.database.repo.requests import RequestsRepo


def is_rating_cached(
    helper_id: int, user_id: int, message_id: int, ratings_cache: dict
) -> bool:
    key = (helper_id, user_id, message_id)
    now = datetime.now()

    if key in ratings_cache:
        # Check if the cache entry is still valid (e.g., within 1 minute)
        if now - ratings_cache[key] < timedelta(minutes=1):
            return True  # It's a duplicate within the time window

    # Update the cache
    ratings_cache[key] = now
    return False


async def change_rating(helper_id: int, change: int, repo: RequestsRepo) -> int:
    current_rating = await repo.rating_users.get_rating_by_user_id(helper_id)
    if not current_rating:
        await repo.rating_users.add_user_for_rating(helper_id, change)
        return change

    # Update the rating
    new_rating = current_rating + change
    await repo.rating_users.update_rating_by_user_id(helper_id, new_rating)

    return new_rating
