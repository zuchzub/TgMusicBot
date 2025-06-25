#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

__all__ = [
    "sec_to_min",
    "get_audio_duration",
]

import asyncio
import json

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
