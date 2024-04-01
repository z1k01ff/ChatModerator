def format_time(seconds: int) -> str:
    """Formats time in a human-readable format.

    Args:
        seconds (int): Time in seconds.

    Returns:
        str: Time formatted in hours (if > 1 hour, rounded to one decimal place),
             minutes (if less than 1 hour), or seconds (if less than 1 minute).
    """
    if seconds >= 3600:  # More than 1 hour
        hours = seconds / 3600
        return f"{hours:.1f} годин"
    elif seconds >= 60:  # Less than 1 hour but more than 1 minute
        minutes = seconds / 60
        return f"{minutes:.1f} хвилин"
    else:  # Less than 1 minute
        return f"{seconds} секунд"
