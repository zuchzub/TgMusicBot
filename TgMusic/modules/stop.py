#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from pytdbot import Client, types

from TgMusic.core import Filter, call
from .funcs import is_admin_or_reply


@Client.on_message(filters=Filter.command(["stop", "end"]))
async def stop_song(c: Client, msg: types.Message) -> None:
    """Stop the current playback and clear the queue."""
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Error):
        c.logger.warning(f"Error in admin check: {chat_id.message}")
        return None

    if isinstance(chat_id, types.Message):
        return None

    _end = await call.end(chat_id)
    if isinstance(_end, types.Error):
        await msg.reply_text(f"⚠️ <b>Error:</b> {_end.message}")
        return None

    await msg.reply_text(
        f"⏹️ Playback stopped by {await msg.mention()}\n" "🔇 The queue has been cleared"
    )
    return None
