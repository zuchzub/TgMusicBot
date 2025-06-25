#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from pytdbot import Client, types

from TgMusic.core import Filter, call
from .funcs import is_admin_or_reply
from .utils.play_helpers import del_msg


@Client.on_message(filters=Filter.command(["skip", "cskip"]))
async def skip_song(c: Client, msg: types.Message) -> None:
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Error):
        c.logger.warning(f"Error sending reply: {chat_id}")
        return None

    if isinstance(chat_id, types.Message):
        return None

    await del_msg(msg)
    await call.play_next(chat_id)
    return None
