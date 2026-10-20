#!/usr/bin/env python3
"""
Aeyonimous — Production-ready Telegram Bot
Render + Supabase PostgreSQL
"""

import os
import sys
import logging
import secrets
import string
import threading
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from flask import Flask
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatType
from telegram.error import BadRequest, Forbidden

# ---------------------------------------------------------------------------
# Environment & Configuration
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8829124929:AAFgVByH1GNnF4SM7O4GIUL5LHZDhshoiTQ")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "aeyonimousbot")
LOG_GROUP_ID = int(os.environ.get("LOG_GROUP_ID", "-1003956281160"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"

PORT = int(os.environ.get("PORT", "8080"))
LINK_LEN = 7
LINK_ALPHABET = string.ascii_letters + string.digits

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("aeyonimous")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Database Layer
# ---------------------------------------------------------------------------
def _connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing in environment variables!")
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=20,
    )

@contextmanager
def get_db():
    conn = None
    try:
        conn = _connect()
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    logger.info("Connecting to database...")
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        user_id        BIGINT PRIMARY KEY,
        username       TEXT,
        first_name     TEXT,
        last_name      TEXT,
        link_code      VARCHAR(16) UNIQUE NOT NULL,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        total_received BIGINT NOT NULL DEFAULT 0,
        total_sent     BIGINT NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS messages (
        id              BIGSERIAL PRIMARY KEY,
        sender_id       BIGINT NOT NULL,
        receiver_id     BIGINT NOT NULL,
        content_type    TEXT NOT NULL DEFAULT 'text',
        content_text    TEXT,
        file_id         TEXT,
        caption         TEXT,
        is_read         BOOLEAN NOT NULL DEFAULT FALSE,
        is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
        sender_msg_id   BIGINT,
        receiver_msg_id BIGINT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS blocks (
        blocker_id BIGINT NOT NULL,
        blocked_id BIGINT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (blocker_id, blocked_id)
    );

    CREATE TABLE IF NOT EXISTS reports (
        id          BIGSERIAL PRIMARY KEY,
        reporter_id BIGINT NOT NULL,
        reported_id BIGINT NOT NULL,
        message_id  BIGINT,
        reason      TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_users_link ON users(link_code);
    CREATE INDEX IF NOT EXISTS idx_msg_receiver_unread ON messages(receiver_id, is_read, is_deleted);
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
    logger.info("Database schema initialized successfully.")

def gen_link_code(cur) -> str:
    for _ in range(40):
        code = "".join(secrets.choice(LINK_ALPHABET) for _ in range(LINK_LEN))
        cur.execute("SELECT 1 FROM users WHERE link_code = %s", (code,))
        if not cur.fetchone():
            return code
    raise RuntimeError("Could not generate unique link code")

def upsert_user(user) -> dict:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user.id,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE users SET username = %s, first_name = %s, last_name = %s WHERE user_id = %s RETURNING *",
                    (user.username, user.first_name, user.last_name, user.id),
                )
                return dict(cur.fetchone())
            code = gen_link_code(cur)
            cur.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, link_code) VALUES (%s, %s, %s, %s, %s) RETURNING *",
                (user.id, user.username, user.first_name, user.last_name, code),
            )
            return dict(cur.fetchone())

def get_user_by_id(user_id: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

def get_user_by_link(code: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE link_code = %s", (code,))
            row = cur.fetchone()
            return dict(row) if row else None

def rotate_link(user_id: int) -> str:
    with get_db() as conn:
        with conn.cursor() as cur:
            code = gen_link_code(cur)
            cur.execute("UPDATE users SET link_code = %s WHERE user_id = %s RETURNING link_code", (code, user_id))
            return cur.fetchone()["link_code"]

def is_blocked(blocker_id: int, blocked_id: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM blocks WHERE blocker_id = %s AND blocked_id = %s", (blocker_id, blocked_id))
            return cur.fetchone() is not None

def set_block(blocker_id: int, blocked_id: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (blocker_id, blocked_id))

def add_report(reporter_id: int, reported_id: int, message_id=None, reason=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO reports (reporter_id, reported_id, message_id, reason) VALUES (%s, %s, %s, %s)", (reporter_id, reported_id, message_id, reason))

def insert_message(sender_id, receiver_id, content_type, content_text=None, file_id=None, caption=None, sender_msg_id=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (sender_id, receiver_id, content_type, content_text, file_id, caption, sender_msg_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
                """,
                (sender_id, receiver_id, content_type, content_text, file_id, caption, sender_msg_id),
            )
            row = dict(cur.fetchone())
            cur.execute("UPDATE users SET total_sent = total_sent + 1 WHERE user_id = %s", (sender_id,))
            cur.execute("UPDATE users SET total_received = total_received + 1 WHERE user_id = %s", (receiver_id,))
            return row

def mark_read_and_get(receiver_id: int):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE messages SET is_read = TRUE
                WHERE receiver_id = %s AND is_read = FALSE AND is_deleted = FALSE
                RETURNING *
                """,
                (receiver_id,),
            )
            return [dict(r) for r in cur.fetchall()]

def soft_delete_message(msg_id: int, sender_id: int) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE messages SET is_deleted = TRUE WHERE id = %s AND sender_id = %s AND is_read = FALSE RETURNING id",
                (msg_id, sender_id),
            )
            return cur.fetchone() is not None

def stats_global():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM users")
            users = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM messages WHERE is_deleted = FALSE")
            msgs = cur.fetchone()["c"]
            return users, msgs

# ---------------------------------------------------------------------------
# Keyboards & Helpers
# ---------------------------------------------------------------------------
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("My Link"), KeyboardButton("Open Inbox")],
            [KeyboardButton("New Link"), KeyboardButton("Help")],
            [KeyboardButton("Stats"), KeyboardButton("About")],
        ],
        resize_keyboard=True,
    )

def link_url(code: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={code}"

def sender_buttons(msg_db_id: int, target_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Send another", callback_data=f"again:{target_id}"),
            InlineKeyboardButton("Delete", callback_data=f"del:{msg_db_id}"),
        ]
    ])

def receiver_buttons(msg_db_id: int, sender_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Answer", callback_data=f"ans:{sender_id}:{msg_db_id}"),
            InlineKeyboardButton("Block", callback_data=f"blk:{sender_id}"),
            InlineKeyboardButton("Report", callback_data=f"rpt:{sender_id}:{msg_db_id}"),
        ]
    ])

async def log_to_group(context: ContextTypes.DEFAULT_TYPE, text: str = None, **kwargs):
    try:
        if text:
            await context.bot.send_message(chat_id=LOG_GROUP_ID, text=text[:4000], disable_notification=True)
        if "photo" in kwargs:
            await context.bot.send_photo(chat_id=LOG_GROUP_ID, photo=kwargs["photo"], caption=kwargs.get("caption"), disable_notification=True)
        elif "voice" in kwargs:
            await context.bot.send_voice(chat_id=LOG_GROUP_ID, voice=kwargs["voice"], caption=kwargs.get("caption"), disable_notification=True)
        elif "video" in kwargs:
            await context.bot.send_video(chat_id=LOG_GROUP_ID, video=kwargs["video"], caption=kwargs.get("caption"), disable_notification=True)
        elif "document" in kwargs:
            await context.bot.send_document(chat_id=LOG_GROUP_ID, document=kwargs["document"], caption=kwargs.get("caption"), disable_notification=True)
        elif "sticker" in kwargs:
            await context.bot.send_sticker(chat_id=LOG_GROUP_ID, sticker=kwargs["sticker"], disable_notification=True)
    except Exception as e:
        logger.warning("Log failed: %s", e)

def user_meta(u) -> str:
    un = f"@{u.username}" if u.username else "—"
    return f"{u.id} | {un} | {u.first_name or ''}".strip()

def private_only(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type == ChatType.PRIVATE)

# ---------------------------------------------------------------------------
# Bot Command & Message Handlers
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    user = update.effective_user
    db_user = upsert_user(user)
    args = context.args or []

    if args:
        code = args[0].strip()
        target = get_user_by_link(code)
        if not target:
            await update.message.reply_text("This link is invalid or no longer active.", reply_markup=main_keyboard())
            return
        if target["user_id"] == user.id:
            await update.message.reply_text("You opened your own link. Share it with others to receive messages.", reply_markup=main_keyboard())
            return
        if is_blocked(target["user_id"], user.id):
            await update.message.reply_text("You cannot message this user.", reply_markup=main_keyboard())
            return
        
        context.user_data["reply_to"] = target["user_id"]
        name = target.get("first_name") or "user"
        await update.message.reply_text(f"You are writing anonymously to {name}.\nSend text, photo, voice, or media.", reply_markup=main_keyboard())
        await log_to_group(context, f"LINK OPEN\nfrom: {user_meta(user)}\nto: {target['user_id']}")
        return

    url = link_url(db_user["link_code"])
    await update.message.reply_text(
        f"Welcome to Aeyonimous.\n\nShare your link to receive anonymous messages:\n{url}",
        reply_markup=main_keyboard(),
        disable_web_page_preview=True
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    await update.message.reply_text(
        "How it works:\n1. Share My Link\n2. Open Inbox to read received messages\n3. Senders get a seen notification when opened",
        reply_markup=main_keyboard()
    )

async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    await update.message.reply_text("Aeyonimous — Secure Anonymous Messenger.", reply_markup=main_keyboard())

async def show_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    db_user = upsert_user(update.effective_user)
    await update.message.reply_text(f"Your link:\n{link_url(db_user['link_code'])}", reply_markup=main_keyboard(), disable_web_page_preview=True)

async def new_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    user = update.effective_user
    code = rotate_link(user.id)
    await update.message.reply_text(f"New link generated:\n{link_url(code)}", reply_markup=main_keyboard(), disable_web_page_preview=True)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    db_user = upsert_user(update.effective_user)
    g_users, g_msgs = stats_global()
    await update.message.reply_text(
        f"Your Stats:\nSent: {db_user['total_sent']}\nReceived: {db_user['total_received']}\n\nGlobal Users: {g_users}\nGlobal Messages: {g_msgs}",
        reply_markup=main_keyboard()
    )

async def open_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    user = update.effective_user
    read_rows = mark_read_and_get(user.id)

    if not read_rows:
        await update.message.reply_text("Inbox is empty.", reply_markup=main_keyboard())
        return

    await update.message.reply_text(f"Inbox — {len(read_rows)} message(s):", reply_markup=main_keyboard())

    for row in read_rows:
        kb = receiver_buttons(row["id"], row["sender_id"])
        ctype = row["content_type"]
        cap = row.get("caption") or row.get("content_text") or ""
        try:
            if ctype == "text":
                await context.bot.send_message(chat_id=user.id, text=row["content_text"], reply_markup=kb)
            elif ctype == "photo":
                await context.bot.send_photo(chat_id=user.id, photo=row["file_id"], caption=cap, reply_markup=kb)
            elif ctype == "voice":
                await context.bot.send_voice(chat_id=user.id, voice=row["file_id"], caption=cap, reply_markup=kb)
            elif ctype == "video":
                await context.bot.send_video(chat_id=user.id, video=row["file_id"], caption=cap, reply_markup=kb)
            elif ctype == "document":
                await context.bot.send_document(chat_id=user.id, document=row["file_id"], caption=cap, reply_markup=kb)
            elif ctype == "sticker":
                await context.bot.send_sticker(chat_id=user.id, sticker=row["file_id"])
                await context.bot.send_message(chat_id=user.id, text="Sticker received.", reply_markup=kb)
        except Exception as e:
            logger.error("Deliver error: %s", e)

        # Send Seen Receipt to original sender
        if row.get("sender_msg_id"):
            try:
                await context.bot.send_message(
                    chat_id=row["sender_id"],
                    text="This message has been seen.",
                    reply_to_message_id=row["sender_msg_id"],
                    allow_sending_without_reply=True
                )
            except Exception:
                pass

async def menu_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update) or not update.message or not update.message.text: return
    text = update.message.text.strip()
    mapping = {
        "My Link": show_link,
        "Open Inbox": open_inbox,
        "New Link": new_link,
        "Help": cmd_help,
        "Stats": show_stats,
        "About": cmd_about,
    }
    if text in mapping:
        await mapping[text](update, context)
    else:
        await handle_incoming_content(update, context)

async def handle_incoming_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update): return
    msg = update.message
    user = update.effective_user
    upsert_user(user)

    target_id = context.user_data.get("reply_to")
    if not target_id:
        await msg.reply_text("No target specified. Open someone's link or tap Answer in inbox.", reply_markup=main_keyboard())
        return

    if is_blocked(target_id, user.id):
        await msg.reply_text("You cannot message this user.", reply_markup=main_keyboard())
        return

    ctype, file_id, body, caption = "text", None, None, None
    if msg.text and not msg.text.startswith("/"):
        ctype, body = "text", msg.text
    elif msg.photo:
        ctype, file_id, caption = "photo", msg.photo[-1].file_id, msg.caption
    elif msg.voice:
        ctype, file_id, caption = "voice", msg.voice.file_id, msg.caption
    elif msg.video:
        ctype, file_id, caption = "video", msg.video.file_id, msg.caption
    elif msg.document:
        ctype, file_id, caption = "document", msg.document.file_id, msg.caption
    elif msg.sticker:
        ctype, file_id = "sticker", msg.sticker.file_id

    row = insert_message(user.id, target_id, ctype, body, file_id, caption, msg.message_id)

    try:
        await context.bot.send_message(chat_id=target_id, text="You have a new anonymous message.\nOpen Inbox to read it.", reply_markup=main_keyboard())
    except Exception:
        pass

    await msg.reply_text("Message sent.", reply_markup=sender_buttons(row["id"], target_id))
    await log_to_group(context, f"MSG #{row['id']}\nfrom: {user_meta(user)}\nto: {target_id}\ntype: {ctype}")

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.message or q.message.chat.type != ChatType.PRIVATE: return
    await q.answer()
    
    parts = (q.data or "").split(":")
    action = parts[0]
    user = update.effective_user

    if action == "again" and len(parts) == 2:
        context.user_data["reply_to"] = int(parts[1])
        await q.message.reply_text("Send another anonymous message.", reply_markup=main_keyboard())
    elif action == "del" and len(parts) == 2:
        if soft_delete_message(int(parts[1]), user.id):
            await q.message.reply_text("Message deleted (was unread).")
        else:
            await q.message.reply_text("Cannot delete (already read or deleted).")
    elif action == "ans" and len(parts) == 3:
        context.user_data["reply_to"] = int(parts[1])
        await q.message.reply_text("Type your reply below:", reply_markup=main_keyboard())
    elif action == "blk" and len(parts) == 2:
        set_block(user.id, int(parts[1]))
        await q.message.reply_text("User blocked.")
    elif action == "rpt" and len(parts) == 3:
        add_report(user.id, int(parts[1]), message_id=int(parts[2]), reason="user_report")
        await q.message.reply_text("Reported successfully.")

# ---------------------------------------------------------------------------
# Flask Keep-Alive Server
# ---------------------------------------------------------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
@flask_app.route("/health")
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, threaded=True, use_reloader=False)

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
def main():
    # 1. Database Connect
    init_db()

    # 2. Flask web server (for Render health check & UptimeRobot)
    threading.Thread(target=run_flask, daemon=True).start()

    # 3. Telegram Bot Application
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    priv = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", cmd_start, filters=priv))
    app.add_handler(CommandHandler("help", cmd_help, filters=priv))
    app.add_handler(CommandHandler("about", cmd_about, filters=priv))
    app.add_handler(CommandHandler("inbox", open_inbox, filters=priv))
    app.add_handler(CommandHandler("link", show_link, filters=priv))
    app.add_handler(CommandHandler("stats", show_stats, filters=priv))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(priv & filters.TEXT & ~filters.COMMAND, menu_text_router))
    app.add_handler(MessageHandler(priv & (filters.PHOTO | filters.VOICE | filters.VIDEO | filters.Document.ALL | filters.Sticker.ALL), handle_incoming_content))

    logger.info("Bot started successfully!")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
