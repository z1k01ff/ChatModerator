import hashlib
import hmac
from urllib.parse import unquote, parse_qsl


from tgbot.config import Config, load_config


config: Config = load_config()


def parse_init_data(init_data: str = None) -> dict:
    if not init_data:
        return {}

    parsed_data = dict(parse_qsl(init_data))
    return parsed_data


def validate_telegram_data(init_data: str) -> bool:
    parsed_data = parse_init_data(init_data)
    received_hash = parsed_data.pop("hash")
    # Constructing the data-check-string
    fields = sorted(
        [(key, unquote(value)) for key, value in parsed_data.items() if key != "hash"]
    )
    # Constructing the data-check-string using the sorted order
    data_check_string = "\n".join(f"{k}={v}" for k, v in fields)

    tokens = [
        config.tg_bot.token,
    ]
    # Attempt to validate against each provided token
    for token in tokens:
        secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if computed_hash == received_hash:
            return True

    return False
