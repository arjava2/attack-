import asyncio
from datetime import datetime
import os
import sys
import time
import traceback
from aiohttp import web
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetBotCallbackAnswerRequest

# ==================== CONFIGURATION ====================
API_ID = 23782654
API_HASH = "5b001caca4f436c940fea5e060f0a3c0"

# String session Render ke Environment Variable se lega
SESSION_STRING = os.environ.get("SESSION_STRING")

TARGET_CHANNELS = [
    # 1. Chatpateee
    "chatpateee",
    -1002133821583,
    # 2. Its Diyaa
    "its_diyaa",
    -1004469467503,
    # 3. Unhinged Aspirand
    "UnhingedAspirand",
    -1003954728685,
    # 4. Channel is Public
    "channelizpublick",
    -1004303326817,
    # 5. Fewmehh
    "fewmehh",
    -1004466801780,
]

LOG_GROUP_ID = -1004402300724
DATA_FILE = "data.txt"

if not SESSION_STRING:
    print(
        "❌ ERROR: SESSION_STRING Environment Variable nahi mila! Render Environment variables check karein."
    )
    sys.exit(1)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


# ==================== CORE EVENT HANDLER ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def whisper_handler(event):
    start_time = time.perf_counter()

    # Auto-Seen
    try:
        asyncio.create_task(
            client.send_read_acknowledge(event.chat_id, max_id=event.id)
        )
    except Exception:
        pass

    if not event.buttons:
        return

    chat_name = event.chat.title if event.chat else "Target Channel"
    print(
        f"\n⚡ [{datetime.now().strftime('%H:%M:%S')}] Whisper Packet Received: [{chat_name}]"
    )

    try:
        secret_text = None

        # Direct Click
        try:
            response = await event.click(0)
            if hasattr(response, "message") and response.message:
                secret_text = response.message
            elif isinstance(response, str):
                secret_text = response
        except Exception:
            pass

        # Raw Callback Fallback
        if not secret_text:
            try:
                btn = event.buttons[0][0]
                if hasattr(btn, "data"):
                    raw_res = await client(
                        GetBotCallbackAnswerRequest(
                            peer=event.chat_id,
                            msg_id=event.id,
                            data=btn.data,
                        )
                    )
                    secret_text = raw_res.message
            except Exception:
                pass

        if not secret_text:
            secret_text = (
                "❌ Secret access nahi mila ya Dusre username ke liye tha"
            )

        # Links
        chat = await event.get_chat()
        if getattr(chat, "username", None):
            msg_link = f"https://t.me/{chat.username}/{event.id}"
            channel_link = f"https://t.me/{chat.username}"
        else:
            clean_id = str(event.chat_id).replace("-100", "")
            msg_link = f"https://t.me/c/{clean_id}/{event.id}"
            channel_link = f"Private ID: {event.chat_id}"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        current_time = datetime.now().strftime("[%d-%m-%Y %H:%M:%S]")

        file_entry = (
            f"{current_time} CHANNEL: {chat_name}\n"
            f"Channel Link: {channel_link}\n"
            f"Message Link: {msg_link}\n"
            f"Execution Time: {elapsed_ms}ms\n"
            f"Secret Message: {secret_text}\n"
            f"{'-'*60}\n"
        )

        with open(DATA_FILE, "a", encoding="utf-8") as f:
            f.write(file_entry)

        log_payload = (
            f"🔓 **Whisper Intercepted & Decoded!**\n\n"
            f"📝 **Secret Message:**\n`{secret_text}`\n\n"
            f"📍 **Channel:** {chat_name}\n"
            f"⚡ **Speed:** `{elapsed_ms} ms`\n"
            f"🔗 [Message Link]({msg_link})"
        )

        await client.send_message(LOG_GROUP_ID, log_payload)
        print(f"✅ Decoded & Forwarded in {elapsed_ms}ms! 👉 {secret_text}")

    except FloodWaitError as e:
        print(f"⚠️ Telegram FloodWait: Sleeping for {e.seconds}s...")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"❌ Execution Error: {e}")
        traceback.print_exc()


# ==================== WEB SERVER (FOR UPTIMEROBOT) ====================
async def handle_ping(request):
    return web.Response(text="Bot is Running 24/7 Active!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web Server started on Port {port}")


# ==================== STARTUP SEQUENCE ====================
async def main():
    print("==================================================")
    print("🚀 PRO WHISPER AUTOMATOR (Cloud Render Engine)")
    print("==================================================")

    await client.start()
    print("🔄 Telegram Connection Established via StringSession!")

    # Start Web Server in Background
    await start_web_server()

    # Pre-load channels
    await client.get_dialogs()

    # Destination Group Verification
    try:
        await client.send_message(
            LOG_GROUP_ID,
            "🚀 **Whisper Automator 24/7 Render Cloud Engine Online!**\nAuto-Seen: `Active`\nData Logging: `Active`",
        )
        print(f"🟢 Log Group Verified: {LOG_GROUP_ID}")
    except Exception as e:
        print(f"🔴 Log Group Warning: {e}")

    print("==================================================")
    print("🔥 Bot Listening 24/7 on Cloud. Ready to capture whispers!")
    print("==================================================\n")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
