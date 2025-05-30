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
        """Initialize the Telegram bot client with configuration validation."""
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

        self.logger.info(
            f"Bot started in {(datetime.now() - StartTime).total_seconds()} seconds"
        )
        self.logger.info(f"Version: {__version__}")

    async def stop(self) -> None:
        """Gracefully shutdown the bot and all services."""
        shutdown_tasks = [
            self.db.close(),
            self.call_manager.stop_scheduler(),
            super().stop(),
        ]
        await asyncio.gather(*shutdown_tasks)

    @staticmethod
    def _validate_config() -> None:
        """Validate all required configuration settings."""
        if not all([config.API_ID, config.API_HASH, config.TOKEN]):
            raise ValueError("API_ID, API_HASH and TOKEN are required")

        if not isinstance(config.MONGO_URI, str):
            raise ValueError("MONGO_URI must be a string")

        if not config.SESSION_STRINGS:
            raise ValueError("No STRING session provided")

        try:
            if config.IGNORE_BACKGROUND_UPDATES and Path("database").exists():
                shutil.rmtree("database")
            DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
            Path("database/photos").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise e


client: Telegram = Telegram()
