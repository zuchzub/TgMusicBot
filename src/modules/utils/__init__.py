#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

__all__ = [
    "Filter",
    "sec_to_min",
    "get_audio_duration",
    "PlayButton",
    "PauseButton",
    "ResumeButton",
    "SupportButton",
    "send_logger",
]

import asyncio
import json

from pytdbot import Client, types

from ._filters import Filter
from .buttons import PauseButton, PlayButton, ResumeButton, SupportButton
from ... import config
from ...helpers import CachedTrack
from ...logger import LOGGER


def sec_to_min(seconds):
    """
    Convert seconds to minutes:second format.
    """
    try:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}:{remaining_seconds:02}"
    except Exception as e:
        LOGGER.warning("Failed to convert seconds to minutes:seconds format: %s", e)
        return None


async def send_logger(client: Client, chat_id, song: CachedTrack):
    """
    Send a message to the logger channel when a song is played.

    Args:
        client (Client): The client to send the message with.
        chat_id (int): The ID of the chat that the song is being played in.
        song (CachedTrack): The song that is being played.

    Returns:
        None
    """
    if not chat_id or not song or chat_id == config.LOGGER_ID or config.LOGGER_ID == 0:
        LOGGER.warning("LOGGER_ID is not set or chat_id is invalid.")
        return

    text = (
        f"<b>Song Playing</b> in <code>{chat_id}</code>\n\n"
        f"▶️ <b>Now Playing:</b> <a href='{song.url}'>{song.name}</a>\n\n"
        f"• <b>Duration:</b> {sec_to_min(song.duration)}\n"
        f"• <b>Requested by:</b> {song.user}\n"
        f"• <b>Platform:</b> {song.platform}"
    )

    msg = await client.sendTextMessage(
        config.LOGGER_ID, text, disable_web_page_preview=True, disable_notification=True
    )
    if isinstance(msg, types.Error):
        LOGGER.error("Error sending message: %s", msg)
    return


async def get_audio_duration(file_path):
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        duration = float(data["format"]["duration"])
        return int(duration)
    except Exception as e:
        LOGGER.warning("Failed to get audio duration using ffprobe: %s", e)
        return 0
