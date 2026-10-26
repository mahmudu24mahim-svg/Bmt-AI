import os
import re
import asyncio
import random
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# BMT FUNNY AI BOT
# =========================

BOT_TOKEN ="8744409329:AAHSUAHCLuotW0VF8ZcKlqvsUFO61rsvpKY"

API_URL = "https://www.gajarbotol.site/apis/deepseek.php"
CREATOR = "@Unkonwn_BMT"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

FUNNY_LINES = [
    "Bhai, tor kotha shune amar AI er matha hang! 😂",
    "Eto talent niye koris ta ki? Ghumash? 💀🤣",
    "Group er obostha dekhe amar digital chokhe pani! 😂",
    "Bhai, amar processor gorom kore dili! 🔥",
    "Tui ekta alada piece! Museum e rakha uchit! 🤣",
    "Admin dekhle valo chele, admin gele abar agun! 😂",
    "Tor logic NASA teo khuje pabe na! 💀",
    "Ami AI, kintu tor kotha shune amio confused! 🤖😂",
]

last_reply = {}
COOLDOWN = 3


# =========================
# RENDER HEALTH SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"BMT Funny AI Bot is running!")

    def log_message(self, format, *args):
        pass


def start_health_server():
    port = int(os.environ.get("PORT", "8080"))

    server = HTTPServer(("0.0.0.0", port), HealthHandler)

    threading.Thread(
        target=server.serve_forever,
        daemon=True,
    ).start()

    logging.info("Health server listening on port %s", port)


# =========================
# DEEPSEEK API
# =========================

def ask_ai(question, is_admin=False):

    if is_admin:
        role = (
            "The user is a Telegram group admin. "
            "Respect them, but be funny and playful."
        )
    else:
        role = (
            "The user is a regular group member. "
            "Talk like a funny Bangladeshi friend."
        )

    prompt = f"""
You are BMT, a funny AI bot in a Bangladeshi Telegram group.

Rules:
- Speak naturally in Bangla or Banglish.
- Be funny, witty, playful and entertaining.
- Give relevant answers to the user's message.
- Use light-hearted jokes and friendly roasts.
- Never be genuinely hateful or abusive.
- Keep answers short and engaging.
- Never pretend to be a human.
- {role}

User message: {question}
"""

    response = requests.get(
        API_URL,
        params={"q": prompt},
        timeout=25,
    )

    response.raise_for_status()

    data = response.json()
    answer = data.get("content", "")

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Empty AI response")

    return answer.strip()


# =========================
# CONTINUOUS TYPING ACTION
# =========================

async def typing_loop(context, chat_id, stop_event):

    while not stop_event.is_set():

        try:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action=ChatAction.TYPING,
            )

        except Exception:
            logging.exception("Typing action failed")

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=4,
            )

        except asyncio.TimeoutError:
            pass


# =========================
# COMMANDS
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.effective_message.reply_text(
        "😂 Assalamu Alaikum! Ami BMT!\n\n"
        "Ami group er Funny AI member! 🤖\n"
        "BMT bole daklei chole ashbo!\n\n"
        f"Created by {CREATOR}"
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.effective_message.reply_text(
        "🤖 BMT Funny AI\n\n"
        "/start - Start bot\n"
        "/help - Help\n\n"
        "BMT, bmt, Bmt — sob kaj korbe! 😂\n"
        "Amar message e reply dileo kotha bolbo!\n\n"
        f"Created by {CREATOR}"
    )


# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not message.text or not user:
        return

    if user.is_bot:
        return

    text = message.text.strip()

    # Check if the message replies to BMT
    replied_to_bot = False

    replied_message = message.reply_to_message

    if replied_message and replied_message.from_user:
        replied_to_bot = (
            replied_message.from_user.id == context.bot.id
        )

    # BMT / bmt / Bmt / BmT
    called_bmt = bool(
        re.search(
            r"(?<!\w)bmt(?!\w)",
            text,
            re.IGNORECASE,
        )
    )

    # Only respond when called or replied to
    if not called_bmt and not replied_to_bot:
        return

    # Per-user cooldown
    key = (chat.id, user.id)

    now = asyncio.get_running_loop().time()

    if now - last_reply.get(key, -100) < COOLDOWN:
        return

    last_reply[key] = now

    # Identify admin
    is_admin = False

    if chat.type in ("group", "supergroup"):

        try:
            member = await context.bot.get_chat_member(
                chat.id,
                user.id,
            )

            is_admin = member.status in (
                "administrator",
                "creator",
            )

        except Exception:
            logging.exception("Admin check failed")

    # Funny intro for admin
    if is_admin and random.random() < 0.25:

        funny_intro = (
            "👑 Admin bhai online! "
            "Baki sobai soja hoye jao! 😂\n\n"
        )

    else:
        funny_intro = ""

    # Start typing while waiting for AI
    stop_typing = asyncio.Event()

    typing_task = asyncio.create_task(
        typing_loop(
            context,
            chat.id,
            stop_typing,
        )
    )

    try:

        answer = await asyncio.to_thread(
            ask_ai,
            text,
            is_admin,
        )

    except Exception:

        logging.exception("AI API request failed")

        answer = random.choice(FUNNY_LINES)

    finally:

        stop_typing.set()

        try:
            await typing_task

        except asyncio.CancelledError:
            pass

    # Add intro and creator signature
    answer = funny_intro + answer

    answer += f"\n\nCreated by {CREATOR}"

    try:

        await message.reply_text(
            answer[:4000]
        )

    except Exception:
        logging.exception("Could not send reply")


# =========================
# START BOT
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable set koro!"
        )

    start_health_server()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    logging.info("BMT Funny AI Bot started!")

    app.run_polling()


if __name__ == "__main__":
    main()
