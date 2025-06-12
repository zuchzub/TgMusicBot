#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import shutil
from datetime import datetime
from pathlib import Path

from pytdbot import Client, types

from src import config
from src.config import COOKIES_URL, DOWNLOADS_DIR
from src.helpers import call, db, start_clients, save_all_cookies, load_translations
from src.modules.jobs import InactiveCallManager

__version__ = "1.2.1"
StartTime = datetime.now()


class Telegram(Client):
    """Main Telegram bot client with extended functionality."""

    def __init__(self) -> None:
        self._validate_config()

        super().__init__(
            token=config.TOKEN,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            default_parse_mode="html",
            td_verbosity=2,
            td_log=types.LogStreamEmpty(),
            plugins=types.plugins.Plugins(folder="src/modules"),
            files_directory="",
            database_encryption_key="",
            options={"ignore_background_updates": config.IGNORE_BACKGROUND_UPDATES},
        )

        self.call_manager = InactiveCallManager(self)
        self.db = db

    async def start(self) -> None:
        """Start the bot and all associated services."""
        await load_translations()
        await save_all_cookies(COOKIES_URL)
        await self.db.ping()
        await start_clients()
        await call.add_bot(self)
        await call.register_decorators()
        await super().start()
        await self.call_manager.start_scheduler()

        uptime = (datetime.now() - StartTime).total_seconds()
        self.logger.info(f"Bot started in {uptime:.2f} seconds")
        self.logger.info(f"Version: {__version__}")

    async def stop(self) -> None:
        """Gracefully shutdown the bot and all services."""
        await asyncio.gather(
            self.db.close(),
            self.call_manager.stop_scheduler(),
            super().stop(),
        )

    @staticmethod
    def _validate_config() -> None:
        """Validate all required environment configuration values."""
        missing = [
            name for name in ("API_ID", "API_HASH", "TOKEN", "MONGO_URI", "LOGGER_ID")
            if not getattr(config, name)
        ]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")

        if not isinstance(config.MONGO_URI, str):
            raise ValueError("MONGO_URI must be a string")

        if not config.SESSION_STRINGS:
            raise ValueError("At least one session string (STRING1–10) is required")

        if config.IGNORE_BACKGROUND_UPDATES:
            db_path = Path("database")
            if db_path.exists():
                shutil.rmtree(db_path)

        try:
            DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
            Path("database/photos").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create required directories: {e}") from e


client: Telegram = Telegram()
