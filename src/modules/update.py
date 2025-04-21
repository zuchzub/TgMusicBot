#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import os
import subprocess as subp
import sys
import uuid
from os import execvp

from pytdbot import Client, types

from src.config import DEVS
from src.helpers import chat_cache
from src.logger import LOGGER
from src.modules.utils import Filter
from src.modules.utils.play_helpers import del_msg


def is_docker():
    """Check if we're running inside a Docker container."""
    return (
        os.path.exists("/.dockerenv")
        or os.path.isfile("/proc/1/cgroup")
        and "docker" in open("/proc/1/cgroup").read()
    )


@Client.on_message(filters=Filter.command(["update", "restart"]))
async def update(c: Client, message: types.Message) -> None:
    """Handle the /update and /restart commands."""
    if message.from_id not in DEVS:
        await del_msg(message)
        return None

    command = message.text.strip().split()[0].lstrip("/")
    msg = await message.reply_text(
        f"{'Updating and ' if command == 'update' else ''}Restarting the bot..."
    )
    if isinstance(msg, types.Error):
        LOGGER.error("Error sending message: %s", msg)
        await message.reply_text(f"⚠️ Something went wrong... {msg.message}")
        return None

    try:
        if command == "update":
            try:
                output = subp.check_output(["git", "pull"], stderr=subp.STDOUT).decode(
                    "utf-8"
                )
                if "Already up to date." in output:
                    msg = await msg.edit_text("✅ Bot is already up to date.")
                    if isinstance(msg, types.Error):
                        LOGGER.error("Error sending message: %s", msg)
                        await message.reply_text(
                            f"⚠️ Something went wrong... {msg.message}"
                        )
                        return None
                    return None

                if len(output) > 4096:
                    filename = f"database/{uuid.uuid4().hex}.txt"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(output)

                    reply = await msg.reply_document(
                        document=types.InputFileLocal(filename),
                        caption="<b>Update log:</b>",
                        parse_mode="html",
                        disable_notification=True,
                    )

                    if isinstance(reply, types.Error):
                        LOGGER.error("Error sending message: %s", reply)
                        await message.reply_text(
                            f"⚠️ Something went wrong... {reply.message}"
                        )
                        return None
                    os.remove(filename)

                else:
                    msg = await msg.edit_text(
                        f"<b>Update Output:</b>\n<pre>{output}</pre>"
                    )
                    if isinstance(msg, types.Error):
                        LOGGER.error("Error sending message: %s", msg)
                        await message.reply_text(
                            f"⚠️ Something went wrong... {msg.message}"
                        )
                        return None

                msg = await msg.edit_text("✅ Bot updated successfully. Restarting...")
                if isinstance(msg, types.Error):
                    LOGGER.error("Error sending message: %s", msg)
                    await message.reply_text(f"⚠️ Something went wrong... {msg.message}")
                    return None

            except subp.CalledProcessError as e:
                LOGGER.error("Error updating bot: %s", e)
                msg = await msg.edit_text(
                    f"⚠️ Update failed:\n<pre>{e.output.decode()}</pre>"
                )
                if isinstance(msg, types.Error):
                    LOGGER.error("Error sending message: %s", msg)
                    await message.reply_text(f"⚠️ Something went wrong... {msg.message}")
                return None

            except Exception as e:
                LOGGER.error("Error updating bot: %s", e)
                await msg.edit_text(f"⚠️ Update error: {e}")
                return None

        if active_vc := chat_cache.get_active_chats():
            for chat_id in active_vc:
                await c.sendTextMessage(chat_id, "♻️ Restarting the bot...")

        # restart the bot
        await msg.edit_text("♻️ Restarting the bot...")
        if is_docker():
            # --restart always if set :)
            await msg.reply_text(
                "🚢 Detected Docker — exiting process to let Docker restart it."
            )
            sys.exit(0)
        else:
            execvp("tgmusic", ["tgmusic"])

    except Exception as e:
        LOGGER.error("Error restarting bot: %s", e)
        await msg.edit_text(f"❌ Failed to restart the bot:\n<pre>{e}</pre>")
        return None
