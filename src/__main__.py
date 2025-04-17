#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from aiofiles import os

import config
from src import client


async def create_directories() -> None:
    """
    Create directories and save cookies.

    This function will create the following directories:
      - `config.DOWNLOADS_DIR`
      - `database/photos`

    It will also call `src.platforms.save_cookies.save_all_cookies` to
    download and save cookies from the URLs in `config.COOKIES_URL`.

    If any error occurs, it will raise a `SystemExit` exception with code 1.
    """
    from src.platforms.save_cookies import save_all_cookies

    try:
        await os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)
        await os.makedirs("database/photos", exist_ok=True)
        await save_all_cookies(config.COOKIES_URL)
    except Exception as e:
        raise SystemExit(1) from e


if __name__ == "__main__":
    client.loop.create_task(create_directories())
    client.run()
