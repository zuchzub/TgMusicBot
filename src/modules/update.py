#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import os
import shutil
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
    """Check if running inside a Docker container."""
    if os.path.exists("/.dockerenv"):
        return True
    if os.path.isfile("/proc/1/cgroup"):
        try:
            with open("/proc/1/cgroup", "r") as f:
                return "docker" in f.read()
        except Exception:
            return False
    return False


@Client.on_message(filters=Filter.command(["update", "restart"]))
async def update(c: Client, message: types.Message) -> None:
    """Handle /update and /restart commands."""
    if message.from_id not in DEVS:
        await del_msg(message)
        return

    command = message.text.strip().split()[0].lstrip("/")
    msg = await message.reply_text(
        f"{'Updating and ' if command == 'update' else ''}Restarting the bot..."
    )

    if command == "update":
        # Ensure .git exists
        if not os.path.exists(".git"):
            await msg.edit_text("⚠️ This instance does not support updates (no .git directory).")
            return

        # Secure way to resolve git-path
        git_path = shutil.which("git") or "/usr/bin/git"
        if not os.path.isfile(git_path):
            await msg.edit_text("❌ Git not found on system.")
            return

        try:
            result = subp.run(
                [git_path, "pull"],
                stdout=subp.PIPE,
                stderr=subp.STDOUT,
                text=True,
                check=True,
            )
            output = result.stdout

            if "Already up to date." in output:
                await msg.edit_text("✅ Bot is already up to date.")
                return

            if len(output) > 4096:
                filename = f"database/{uuid.uuid4().hex}.txt"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(output)

                await msg.reply_document(
                    document=types.InputFileLocal(filename),
                    caption="<b>Update log:</b>",
                    parse_mode="html",
                    disable_notification=True,
                )
                os.remove(filename)
            else:
                await msg.edit_text(f"<b>Update Output:</b>\n<pre>{output}</pre>")
            await msg.edit_text("✅ Bot updated successfully. Restarting...")

        except subp.CalledProcessError as e:
            LOGGER.error("Update failed: %s", e)
            await msg.edit_text(f"⚠️ Update failed:\n<pre>{e.output}</pre>")
            return
        except Exception as e:
            LOGGER.error("Unexpected update error: %s", e)
            await msg.edit_text(f"⚠️ Update error: {e}")
            return

    # Inform active chats
    if active_vc := chat_cache.get_active_chats():
        for chat_id in active_vc:
            await c.sendTextMessage(chat_id, "♻️ Restarting the bot...")

    await msg.edit_text("♻️ Restarting the bot...")

    # Restart logic
    if is_docker():
        await msg.reply_text("🚢 Detected Docker — exiting process to let Docker restart it.")
        sys.exit(0)
    else:
        tgmusic_path = shutil.which("tgmusic")
        if not tgmusic_path:
            await msg.edit_text("❌ Unable to find 'tgmusic' in PATH.")
            return
        execvp("tgmusic", ["tgmusic"])
