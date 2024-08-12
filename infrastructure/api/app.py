from contextlib import suppress
import json
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
import random
from typing import List
import time

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

# Rate limiting
RATE_LIMIT = 2  # requests per second
last_request_time = {}

def check_rate_limit(user_id: int):
    current_time = time.time()
    if user_id in last_request_time:
        time_passed = current_time - last_request_time[user_id]
        if time_passed < 1 / RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    last_request_time[user_id] = current_time


class ShareResultsRequest(BaseModel):
    user_id: int
    session_result: int
    InitData: str

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
WEIGHTS = [70, 55, 50, 10, 3]

def get_random_symbol():
    return random.choices(SYMBOLS, weights=WEIGHTS, k=1)[0]

def calculate_winnings(result: List[str], stake: int) -> int:
    if len(set(result)) == 1:  # All symbols are the same
        symbol = result[0]
        multiplier = {
            "7️⃣": 1000,
            "🎰": 200,
            "🍇": 25,
            "🍒": 13,
            "🍋": 8,
        }.get(symbol, 0)
        return stake * multiplier
    return 0

router = APIRouter(prefix="/chatmoderator/api")

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user_id: int):
    async with session_pool() as session:
        repo = RequestsRepo(session)
        balance = await get_user_balance(user_id, repo)
    return {"balance": balance}

@router.post("/spin", response_model=SpinResponse)
async def spin(request: SpinRequest):
    print(request.model_dump())
    check_rate_limit(request.user_id)

    if not request.InitData or not validate_telegram_data(request.InitData):
        raise HTTPException(status_code=400, detail="Invalid initData")
    
    init_data = parse_init_data(request.InitData)
    user = json.loads(init_data.get("user", "{}"))
    if user.get("id") != request.user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")

    if request.stake <= 0:
        raise HTTPException(status_code=400, detail="Stake must be positive")

    async with session_pool() as session:
        repo = RequestsRepo(session)
        current_balance = await get_user_balance(request.user_id, repo)

        if current_balance < request.stake:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        result = [get_random_symbol() for _ in range(3)]
        winAmount = calculate_winnings(result, request.stake)
        newBalance = current_balance - request.stake + winAmount
        action = "win" if winAmount > 0 else "lose"

        print(f"Result: {result}, action: {action}, winAmount: {winAmount}, newBalance: {newBalance}")
        await update_user_balance(request.user_id, newBalance, repo)

        data = parse_init_data(request.InitData)
        if action == "win":
            try:
                user = json.loads(data.get("user", "{}"))
                first_name = user.get("first_name", "")
                last_name = user.get("last_name", "")
                full_name = f"{first_name} {last_name}" if last_name else first_name
                name_with_mention = f'<a href="tg://user?id={request.user_id}">{full_name}</a>'
                prize = " ".join(result)
                success_message = f"Користувач {name_with_mention} вибив {prize} і отримав {winAmount} рейтингу, тепер у нього {newBalance} рейтингу.\nВітаємо!"
                with suppress(Exception):
                    await bot.send_message(
                        chat_id=request.user_id,
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
                        disable_notification=True,
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

@app.on_event("shutdown")
async def shutdown_event():
    await bot.session.close()