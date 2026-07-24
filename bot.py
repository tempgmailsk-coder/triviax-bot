"""
Telegram Trivia/Quiz Bot
------------------------
Pulls random trivia questions from the free Open Trivia Database (opentdb.com)
and lets a single user play solo, tracking their score in memory.

Setup:
    pip install python-telegram-bot==21.* html5lib

Run:
    python bot.py

Commands:
    /start   - welcome message
    /quiz    - get a new trivia question
    /score   - show your current score
    /help    - list commands
"""

import html
import logging
import random

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

BOT_TOKEN = "8535067874:AAGopQ09DvqJQo8Jpl0DS4nEuoRZ58WGcpk"  # <-- your bot token
TRIVIA_API_URL = "https://opentdb.com/api.php?amount=1&type=multiple"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory storage: { user_id: {"score": int, "answered": int} }
user_scores: dict[int, dict[str, int]] = {}

# In-memory storage for the currently active question per chat:
# { chat_id: {"correct": str, "options": list[str]} }
active_questions: dict[int, dict] = {}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

async def fetch_question() -> dict:
    """Fetch a single random trivia question from Open Trivia DB."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(TRIVIA_API_URL)
        resp.raise_for_status()
        data = resp.json()

    result = data["results"][0]
    question = html.unescape(result["question"])
    correct = html.unescape(result["correct_answer"])
    incorrect = [html.unescape(a) for a in result["incorrect_answers"]]

    options = incorrect + [correct]
    random.shuffle(options)

    return {
        "question": question,
        "category": html.unescape(result["category"]),
        "difficulty": result["difficulty"],
        "correct": correct,
        "options": options,
    }


def get_user_stats(user_id: int) -> dict:
    return user_scores.setdefault(user_id, {"score": 0, "answered": 0})


# ----------------------------------------------------------------------------
# Command handlers
# ----------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome to Trivia Bot!\n\n"
        "Use /quiz to get a question, /score to check your score, "
        "and /help to see all commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/quiz - get a new trivia question\n"
        "/score - show your current score\n"
        "/help - show this message"
    )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    try:
        q = await fetch_question()
    except Exception as exc:  # network / API errors
        logger.exception("Failed to fetch question")
        await update.message.reply_text(
            "Couldn't fetch a question right now, try /quiz again in a moment."
        )
        return

    active_questions[chat_id] = {
        "correct": q["correct"],
        "options": q["options"],
    }

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=opt)] for opt in q["options"]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"📚 Category: {q['category']}\n"
        f"🎯 Difficulty: {q['difficulty'].capitalize()}\n\n"
        f"❓ {q['question']}"
    )
    await update.message.reply_text(text, reply_markup=markup)


async def score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = get_user_stats(update.effective_user.id)
    await update.message.reply_text(
        f"🏆 Your score: {stats['score']} / {stats['answered']} answered"
    )


async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chosen = query.data

    active = active_questions.get(chat_id)
    await query.answer()  # acknowledge the tap

    if not active:
        await query.edit_message_text("This question has expired. Use /quiz for a new one.")
        return

    stats = get_user_stats(user_id)
    stats["answered"] += 1

    correct = active["correct"]
    if chosen == correct:
        stats["score"] += 1
        result_text = f"✅ Correct! The answer was: {correct}"
    else:
        result_text = f"❌ Wrong. You picked '{chosen}'. Correct answer: {correct}"

    del active_questions[chat_id]

    await query.edit_message_text(
        f"{result_text}\n\nScore: {stats['score']} / {stats['answered']}\n"
        f"Use /quiz for another question!"
    )


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CallbackQueryHandler(answer_callback))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
