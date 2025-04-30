#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import subprocess

from pytdbot import Client, types

from src.config import DEVS
from src.helpers import Telegram
from src.logger import LOGGER
from src.modules.utils import Filter
from src.modules.utils.play_helpers import edit_text, del_msg, extract_argument


async def stream(stream_url: str, path: str) -> bool:
    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        path,
        "-c:v",
        "libx264",
        "-preset",
        "superfast",
        "-b:v",
        "2000k",
        "-maxrate",
        "2000k",
        "-bufsize",
        "4000k",
        "-pix_fmt",
        "yuv420p",
        "-g",
        "30",
        "-threads",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-f",
        "flv",
        "-rtmp_buffer",
        "100",
        "-rtmp_live",
        "live",
        stream_url,
    ]

    try:
        LOGGER.info(f"Starting FFmpeg stream from {path} to {stream_url}")
        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        # Wait for a process to complete
        return_code = ffmpeg_proc.wait()
        if return_code == 0:
            LOGGER.info("FFmpeg stream completed successfully")
            return True

        stderr = ffmpeg_proc.stderr.read()
        LOGGER.error(f"FFmpeg failed with return code {return_code}:\n{stderr}")
        return False

    except subprocess.SubprocessError as e:
        LOGGER.error(f"FFmpeg subprocess error: {str(e)}")
        return False
    except Exception as e:
        LOGGER.error(f"Unexpected error during streaming: {str(e)}")
        return False


@Client.on_message(filters=Filter.command("stream"))
async def stream_cmd(_: Client, msg: types.Message) -> None:
    """Handle the /stream command to stream replied media to RTMP server."""
    if msg.from_id not in DEVS:
        await del_msg(msg)
        return

    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    telegram = Telegram(reply)

    if not telegram.is_valid():
        await msg.reply_text("❌ Reply to a valid video or audio file.")
        return

    reply_message = await msg.reply_text("📥 Downloading file...")

    file_path, file_name = await telegram.dl(reply_message)
    if isinstance(file_path, types.Error):
        await edit_text(
            reply_message,
            text=(
                "❌ <b>Download Failed</b>\n\n"
                f"🎶 <b>File:</b> <code>{file_name}</code>\n"
                f"💬 <b>Error:</b> <code>{file_path.message}</code>"
            ),
        )
        return

    stream_url = extract_argument(msg.text)
    if not stream_url:
        await edit_text(reply_message, "❌ Please provide RTMP stream URL.")
        return

    await edit_text(reply_message, "📡 Starting stream...")
    success = await stream(stream_url, file_path.path)
    if success:
        await edit_text(reply_message, "✅ Streaming completed successfully!")
    else:
        await edit_text(reply_message, "❌ Streaming failed. Check logs for details.")
