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

# ==================== PREMIUM FORMATTER ====================
def premium_format(content, chat_name, speed, link, is_media=False):
    media_tag = " [ᴀᴅᴠᴀɴᴄᴇᴅ ᴍᴇᴅɪᴀ]" if is_media else ""
    now = datetime.now().strftime("%I:%M %p")
    
    text = (
        f"💎 **ᴡʜɪsᴘᴇʀ ɪɴᴛᴇʀᴄᴇᴘᴛᴇᴅ** {media_tag}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 **ᴍᴇssᴀɢᴇ:**\n`{content}`\n\n"
        f"📍 **ᴄʜᴀɴɴᴇʟ:** `{chat_name}`\n"
        f"⚡ **ʟᴀᴛᴇɴᴄʏ:** `{speed} ᴍs`\n"
        f"🕒 **ᴛɪᴍᴇ:** `{now}`\n\n"
        f"🔗 **ʟɪɴᴋ:** [ᴏᴘᴇɴ ᴍᴇssᴀɢᴇ]({link})\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    return text

# ==================== HELPERS ====================
async def get_msg_link(event):
    try:
        chat = await event.get_chat()
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}/{event.id}"
        return f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
    except: return "#"

# ==================== HANDLERS ====================
@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def channel_handler(event):
    if not event.buttons: return
    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    msg_link = await get_msg_link(event)
    print(f"🔍 Intercepting: {chat_name}", flush=True)

    try:
        payload = None
        for row in event.buttons:
            for btn in row:
                if btn.url and 'PsstRobot?start=' in btn.url:
                    payload = btn.url.split('start=')[-1]

        res = await event.click(0)
        popup_text = ""
        if hasattr(res, 'message') and res.message: popup_text = res.message
        elif isinstance(res, str): popup_text = res

        if popup_text and "-wh::" in popup_text:
            match = re.search(r"-wh::[a-zA-Z0-9_=]+", popup_text)
            if match: payload = match.group(0)

        if payload or "advanced" in popup_text.lower():
            ctx.update({"title": chat_name, "link": msg_link, "time": start_time})
            await client.send_message(WHISPER_BOT_ID, f"/start {payload}" if payload else "/start")
        elif popup_text:
            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            await client.send_message(LOG_GROUP_ID, premium_format(popup_text, chat_name, elapsed, msg_link), link_preview=False)

    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    if event.buttons:
        await event.click(0)
        return
    if event.message.text and any(x in event.message.text for x in ["Preparing", "/start"]): return

    try:
        now = time.perf_counter()
        if now - ctx["time"] > 120: ctx["time"] = now 
        elapsed = round((now - ctx["time"]) * 1000, 2)
        
        media_info = "ᴘʜᴏᴛᴏ/ᴍᴇᴅɪᴀ ᴄᴏɴᴛᴇɴᴛ"
        formatted_text = premium_format(event.message.text or media_info, ctx['title'], elapsed, ctx['link'], is_media=True)
        
        await client.send_message(LOG_GROUP_ID, formatted_text, file=event.message.media if event.message.media else None, link_preview=False)
        await client.send_read_acknowledge(event.chat_id)
    except Exception as e:
        print(f"❌ DM Error: {e}", flush=True)

# ==================== STARTUP ====================
async def handle_ping(request): return web.Response(text="Bot Active")
async def main():
    await client.start()
    app = web.Application(); app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    await client.get_dialogs()
    
    # Elite Startup Message
    startup_msg = (
        "🛡️ **ᴡʜɪsᴘᴇʀ ᴀᴜᴛᴏᴍᴀᴛᴏʀ ᴘʀᴏ: ᴏɴʟɪɴᴇ**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🚀 **ᴇɴɢɪɴᴇ:** `ᴠ.2.0 (ᴇʟɪᴛᴇ)`\n"
        "💎 **sᴛᴀᴛᴜs:** `ʀᴇᴀᴅʏ ᴛᴏ ᴅᴇᴄᴏᴅᴇ`\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await client.send_message(LOG_GROUP_ID, startup_msg)
    print("🟢 ELITE ENGINE ACTIVE", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__": asyncio.run(main())
