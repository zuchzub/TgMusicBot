# Copyright (c) 2025 AshokShau
# Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrogram import Client as PyroClient
from pyrogram import errors
from pytdbot import Client, types

from TgMusic.core import chat_cache, config, call, db


class InactiveCallManager:
    def __init__(self, bot: Client):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(
            timezone="Asia/Kolkata",
            job_defaults={
                'misfire_grace_time': 120,
                'max_instances': 1,
                'coalesce': True
            }
        )
        self._concurrency_limiter = asyncio.Semaphore(5)
        self._active_tasks = set()

    async def _end_call(self, chat_id: int) -> bool:
        try:
            vc_users = await call.vc_users(chat_id)
            if isinstance(vc_users, types.Error):
                self.bot.logger.warning(
                    f"Error getting vc users in {chat_id}: {vc_users.message}"
                )
                return False

            if len(vc_users) > 1:
                return False

            played_time = await call.played_time(chat_id)
            if isinstance(played_time, types.Error):
                self.bot.logger.warning(
                    f"Error getting played time in {chat_id}: {played_time.message}"
                )
                return False

            if played_time < 15:
                return False

            reply = await self.bot.sendTextMessage(
                chat_id, "⚠️ No active listeners detected. ⏹️ Leaving voice chat..."
            )
            if isinstance(reply, types.Error):
                self.bot.logger.warning(f"Error sending message in {chat_id}: {reply}")

            end_result = await call.end(chat_id)
            if isinstance(end_result, types.Error):
                self.bot.logger.warning(f"Error ending call in {chat_id}: {end_result}")
                return False

            return True
        except Exception as e:
            self.bot.logger.error(
                f"Unexpected error in _safe_end_call for {chat_id}: {str(e)}",
                exc_info=True
            )
            return False

    async def _process_chat_batch(self, chat_ids: list[int]):
        """Process a batch of chats with proper concurrency control."""
        tasks = []
        for chat_id in chat_ids:
            task = asyncio.create_task(self._end_call(chat_id))
            self._active_tasks.add(task)
            task.add_done_callback(lambda t: self._active_tasks.discard(t))
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def end_inactive_calls(self):
        if not self.bot or not self.bot.me:
            return
        try:
            if not await db.get_auto_end(self.bot.me.id):
                return

            active_chats = chat_cache.get_active_chats()
            if not active_chats:
                self.bot.logger.debug("No active chats to process")
                return

            self.bot.logger.info(f"Processing {len(active_chats)} active chats")
            batch_size = 5
            for i in range(0, len(active_chats), batch_size):
                batch = active_chats[i:i + batch_size]
                await self._process_chat_batch(batch)
                await asyncio.sleep(0.5)
        except Exception as e:
            self.bot.logger.critical(
                f"Critical error in end_inactive_calls: {str(e)}",
                exc_info=True
            )

    async def _leave_chat(self, ub: PyroClient, chat_id: int):
        try:
            if chat_cache.is_active(chat_id):
                return False

            await ub.leave_chat(chat_id)
            self.bot.logger.debug(f"[{ub.name}] Successfully left chat {chat_id}")
            return True
        except errors.FloodWait as e:
            wait_time = e.value
            if wait_time <= 100:
                self.bot.logger.warning(
                    f"[{ub.name}] FloodWait {wait_time}s for chat {chat_id}"
                )
                await asyncio.sleep(wait_time)
                return await self._leave_chat(ub, chat_id)
            return False
        except errors.RPCError as e:
            self.bot.logger.warning(
                f"[{ub.name}] RPCError leaving chat {chat_id}: {e}"
            )
            return False
        except Exception as e:
            self.bot.logger.error(
                f"[{ub.name}] Error leaving chat {chat_id}: {str(e)}",
                exc_info=True
            )
            return False

    async def leave_all(self):
        if not config.AUTO_LEAVE:
            return

        self.bot.logger.info("Starting leave_all task")
        start_time = time.monotonic()

        try:
            for client_name, call_instance in call.calls.items():
                ub: PyroClient = call_instance.mtproto_client
                chats_to_leave = []

                try:
                    async for dialog in ub.get_dialogs():
                        chat = getattr(dialog, "chat", None)
                        if chat and chat.id > 0:
                            continue
                        chats_to_leave.append(chat.id)
                except Exception as e:
                    self.bot.logger.error(
                        f"[{client_name}] Error getting dialogs: {str(e)}",
                        exc_info=True
                    )
                    continue

                self.bot.logger.info(
                    f"[{client_name}] Processing {len(chats_to_leave)} chats"
                )
                for chat_id in chats_to_leave:
                    await self._leave_chat(ub, chat_id)
                    await asyncio.sleep(0.5)

        except Exception as e:
            self.bot.logger.critical(
                f"Critical error in leave_all: {str(e)}",
                exc_info=True
            )
        finally:
            duration = time.monotonic() - start_time
            self.bot.logger.info(f"Completed leave_all in {duration:.2f} seconds")

    async def start_scheduler(self):
        self.scheduler.add_job(
            self.end_inactive_calls,
            CronTrigger(minute="*/1"),
            id="end_inactive_calls",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.leave_all,
            CronTrigger(hour=3),
            id="leave_all",
            replace_existing=True
        )

        self.scheduler.start()
        self.bot.logger.info("Scheduler started successfully")

    async def stop_scheduler(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            for task in self._active_tasks:
                task.cancel()
            await asyncio.gather(
                *self._active_tasks,
                return_exceptions=True
            )
            self.bot.logger.info("Scheduler stopped successfully")
