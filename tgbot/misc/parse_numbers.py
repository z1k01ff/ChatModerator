import logging
import sys
from random import randint
from typing import Optional


def generate_num(
        min_num: Optional[str] = None,
        max_num: Optional[str] = None,
        min_default: int = 1,
        max_default: int = 100,
) -> int:
    # Define a function to safely convert string to int with boundaries
    def safe_int(num_str: Optional[str], default: int, lower_bound: int = 0,
                 upper_bound: int = sys.maxsize) -> int:
        try:
            num = int(num_str) if num_str else default
            return max(lower_bound, min(num, upper_bound))
        except ValueError as e:
            logging.error(e)
            return default

    # Convert min_num and max_num to integers safely
    min_val = safe_int(min_num, min_default)
    max_val = safe_int(max_num, max_default if not min_num else min_val)

    # Ensure min_val is not greater than max_val
    min_val, max_val = min(min_val, max_val), max(max_val, min_val)

    # Generate and return the random number
    return randint(min_val, max_val)
