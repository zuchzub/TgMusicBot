#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import time
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrogram import Client as PyroClient
from pyrogram import errors
from pytdbot import Client, types

from TgMusic.core import chat_cache, config, call, db

_concurrency_limiter = asyncio.Semaphore(10)


class InactiveCallManager:
    def __init__(self, bot: Client):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(
            timezone="Asia/Kolkata", event_loop=self.bot.loop
        )

    async def _end_inactive_calls(self, chat_id: int):
        async with _concurrency_limiter:
            vc_users = await call.vc_users(chat_id)
            if isinstance(vc_users, types.Error):
                self.bot.logger.warning(
                    f"An error occurred while getting vc users: {vc_users.message}"
                )
                return

            if len(vc_users) > 1:
                return
            played_time = await call.played_time(chat_id)
            if isinstance(played_time, types.Error):
                self.bot.logger.warning(
                    f"An error occurred while getting played time: {played_time.message}"
                )
                return

            if played_time < 15:
                return

            reply = await self.bot.sendTextMessage(
                chat_id, "⚠️ No active listeners detected. ⏹️ Leaving voice chat..."
            )
            if isinstance(reply, types.Error):
                self.bot.logger.warning(f"Error sending message: {reply}")
            await call.end(chat_id)

    async def end_inactive_calls(self):
        if self.bot is None or self.bot.me is None:
            return
        if not await db.get_auto_end(self.bot.me.id):
            return

        active_chats = chat_cache.get_active_chats()
        if not active_chats:
            self.bot.logger.debug("No active chats found.")
            return

        start_time = datetime.now()
        start_monotonic = time.monotonic()
        self.bot.logger.debug(
            f"🔄 Started end_inactive_calls at {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            self.bot.logger.debug(f"Checking {len(active_chats)} active chats...")
            tasks = [self._end_inactive_calls(chat_id) for chat_id in active_chats]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.bot.logger.error(
                f"❗ Exception in end_inactive_calls: {e}", exc_info=True
            )
        finally:
            end_time = datetime.now()
            duration = time.monotonic() - start_monotonic
            self.bot.logger.debug(
                f"✅ Finished end_inactive_calls at {end_time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(Duration: {duration:.2f}s)"
            )

    async def leave_all(self):
        if not config.AUTO_LEAVE:
            return

        for client_name, call_instance in call.calls.items():
            ub: PyroClient = call_instance.mtproto_client
            chats_to_leave = []
            async for dialog in ub.get_dialogs():
                chat = getattr(dialog, "chat", None)
                if not chat:
                    continue
                if chat.id > 0:
                    self.bot.logger.debug(
                        f"[{client_name}] Skipping private chat: {chat.id}"
                    )
                    continue
                chats_to_leave.append(chat.id)
            self.bot.logger.debug(
                f"[{client_name}] Found {len(chats_to_leave)} chats to leave."
            )

            for chat_id in chats_to_leave:
                is_active = chat_cache.is_active(chat_id)
                if is_active:
                    continue
                try:
                    await ub.leave_chat(chat_id)
                    self.bot.logger.debug(f"[{client_name}] Left chat {chat_id}")
                    await asyncio.sleep(0.5)
                except errors.FloodWait as e:
                    wait_time = e.value
                    self.bot.logger.warning(
                        f"[{client_name}] FloodWait for {wait_time}s on chat {chat_id}"
                    )
                    if wait_time > 100:
                        self.bot.logger.warning(
                            f"[{client_name}] Skipping due to long wait time."
                        )
                        continue
                    await asyncio.sleep(wait_time)
                except errors.RPCError as e:
                    self.bot.logger.warning(
                        f"[{client_name}] Failed to leave chat {chat_id}: {e}"
                    )
                    continue
                except Exception as e:
                    self.bot.logger.error(
                        f"[{client_name}] Error leaving chat {chat_id}: {e}"
                    )
                    continue

            self.bot.logger.info(f"[{client_name}] Leaving all chats completed.")

    async def start_scheduler(self):
        self.scheduler.add_job(
            self.end_inactive_calls,
            CronTrigger(minute="*/1"),
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.add_job(self.leave_all, CronTrigger(hour=0, minute=0))
        self.scheduler.start()
        self.bot.logger.info("Scheduler started.")

    async def stop_scheduler(self):
        self.scheduler.shutdown(wait=True)
        await asyncio.sleep(1)
        self.bot.logger.info("Scheduler stopped.")
