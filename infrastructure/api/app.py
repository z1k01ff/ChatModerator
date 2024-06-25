import json
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
import random
from typing import List

from starlette.middleware.cors import CORSMiddleware

from infrastructure.api.utils import parse_init_data, validate_telegram_data
from infrastructure.database.repo.requests import RequestsRepo
from infrastructure.database.setup import create_engine, create_session_pool
from tgbot.config import load_config

app = FastAPI()
config = load_config()
engine = create_engine(config.db.construct_sqlalchemy_url())
session_pool = create_session_pool(engine)
bot = Bot(token=config.tg_bot.token)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ShareResultsRequest(BaseModel):
    user_id: int
    session_result: int
    InitData: str


# Create a bot instance
# Pydantic models
class BalanceResponse(BaseModel):
    balance: int


class SpinRequest(BaseModel):
    user_id: int
    stake: int
    InitData: str


class SpinResponse(BaseModel):
    result: List[str]
    action: str
    winAmount: int
    newBalance: int


async def get_user_balance(user_id: int, repo: RequestsRepo) -> int:
    return await repo.rating_users.get_rating_by_user_id(user_id) or 0


async def update_user_balance(
    user_id: int, new_balance: int, repo: RequestsRepo
) -> None:
    await repo.rating_users.update_rating_by_user_id(user_id, new_balance)


# Game logic
SYMBOLS = ["🍋", "🍒", "🍇", "🎰", "7️⃣"]
WEIGHTS = [50, 50, 30, 15, 5]


def get_random_symbol():
    return random.choices(SYMBOLS, weights=WEIGHTS, k=1)[0]


def calculate_winnings(result: List[str], stake: int) -> int:
    if len(set(result)) == 1:  # All symbols are the same
        symbol = result[0]

        multiplier = {
            "7️⃣": 1500,
            "🎰": 500,
            "🍇": 30,
            "🍒": 10,
            "🍋": 2,
        }.get(symbol, 0)
        return stake * multiplier
    return 0


router = APIRouter(prefix="/chatmoderator/api")


# API endpoints
@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user_id: int):
    async with session_pool() as session:
        repo = RequestsRepo(session)
        balance = await get_user_balance(user_id, repo)
    return {"balance": balance}


@router.post("/spin", response_model=SpinResponse)
async def spin(request: SpinRequest):
    if not request.InitData or not validate_telegram_data(request.InitData):
        raise HTTPException(status_code=400, detail="Invalid initData")

    async with session_pool() as session:
        repo = RequestsRepo(session)
        current_balance = await get_user_balance(request.user_id, repo)

        if current_balance < request.stake:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        result = [get_random_symbol() for _ in range(3)]
        winAmount = calculate_winnings(result, request.stake)
        newBalance = current_balance - request.stake + winAmount
        action = "win" if winAmount > 0 else "lose"

        await update_user_balance(request.user_id, newBalance, repo)

        data = parse_init_data(request.InitData)
        if action == "win" and "🍋" not in result and "🍒" not in result:
            try:
                user = data.get("user")
                user = json.loads(user)
                first_name = user.get("first_name")
                last_name = user.get("last_name")
                full_name = f"{first_name} {last_name}" if last_name else first_name
                name_with_mention = (
                    f'<a href="tg://user?id={request.user_id}">{full_name}</a>'
                )
                prize = " ".join(result)
                success_message = f"Користувач {name_with_mention} вибив {prize} і отримав {winAmount} рейтингу, тепер у нього {newBalance} рейтингу.\nВітаємо!"
                await bot.send_message(
                    chat_id=-1001415356906,
                    text=success_message,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="🎰 Зіграти теж!",
                                    url="https://t.me/Latandbot/casino",
                                )
                            ]
                        ]
                    ),
                )
            except Exception as e:
                logging.error(f"Error sending message: {e}")

    return {
        "result": result,
        "action": action,
        "winAmount": winAmount,
        "newBalance": newBalance,
    }


app.include_router(router)


# Make sure to close the bot session when the app shuts down
@app.on_event("shutdown")
async def shutdown_event():
    await bot.session.close()
