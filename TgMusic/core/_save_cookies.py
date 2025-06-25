#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import os
import uuid
from urllib.parse import urlparse

import aiofiles
import aiohttp

from TgMusic.logger import LOGGER


async def fetch_content(session: aiohttp.ClientSession, url: str) -> str | None:
    """Fetches content from BatBin or Pastebin."""
    paste_id = url.strip("/").split("/")[-1]

    if "pastebin.com" in url:
        raw_url = f"https://pastebin.com/raw/{paste_id}"
    else:
        raw_url = f"https://batbin.me/raw/{paste_id}"

    try:
        async with session.get(raw_url) as response:
            if response.status == 200:
                content_type = response.headers.get("Content-Type", "")
                if "text/plain" in content_type or "text" in content_type:
                    return await response.text()
                LOGGER.error(
                    "Unexpected Content-Type (%s) from %s", content_type, raw_url
                )
            else:
                LOGGER.error("Failed to download %s: %s", raw_url, response.status)
    except Exception as e:
        LOGGER.error("Error fetching %s: %s", raw_url, e)

    return None


async def save_bin_content(session: aiohttp.ClientSession, url: str) -> str | None:
    """
    Downloads content from BatBin and saves it as a .txt file.
    """
    parsed = urlparse(url)
    filename = (
        (parsed.path.strip("/").split("/")[-1] or str(uuid.uuid4()).split("-")[0])
        .split("?")[0]
        .split("#")[0]
    )
    filename += ".txt"
    filepath = os.path.join("TgMusic/cookies", filename)

    content = await fetch_content(session, url)
    if content:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            async with aiofiles.open(filepath, "w") as f:
                await f.write(content)
            return filepath
        except Exception as e:
            LOGGER.error("Error saving file %s: %s", filepath, e)

    return None


async def save_all_cookies(cookie_urls: list[str]) -> list[str]:
    """
    Processes multiple URLs concurrently and returns saved file paths.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [save_bin_content(session, url) for url in cookie_urls]
        results = await asyncio.gather(*tasks)

    return [res for res in results if res]
