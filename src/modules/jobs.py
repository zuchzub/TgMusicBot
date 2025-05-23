#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrogram import Client as PyroClient
from pyrogram import errors
from pytdbot import Client, types

from src import db
from src.config import AUTO_LEAVE
from src.helpers import call
from src.helpers import chat_cache


class InactiveCallManager:
    def __init__(self, bot: Client):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(
            timezone="Asia/Kolkata", event_loop=self.bot.loop
        )
        self._lock = asyncio.Lock()

    async def _end_inactive_calls(self, chat_id: int, semaphore: asyncio.Semaphore):
        async with semaphore:
            vc_users = await call.vc_users(chat_id)
            if isinstance(vc_users, types.Error):
                self.bot.logger.warning(
                    f"An error occurred while getting vc users: {vc_users.message}"
                )
                return

            if len(vc_users) > 1:
                self.bot.logger.debug(
                    f"Active users detected in chat {chat_id}. Skipping..."
                )
                return

            # Check if the call has been active for more than 20 seconds
            played_time = await call.played_time(chat_id)
            if isinstance(played_time, types.Error):
                self.bot.logger.warning(
                    f"An error occurred while getting played time: {played_time.message}"
                )
                return
            if played_time < 20:
                self.bot.logger.debug(
                    f"Call in chat {chat_id} has been active for less than 20 "
                    "seconds. Skipping..."
                )
                return

            # Notify the chat and end the call
            _chat_id = await db.get_chat_id_by_channel(chat_id) or chat_id
            reply = await self.bot.sendTextMessage(
                _chat_id, "⚠️ No active listeners detected. ⏹️ Leaving voice chat..."
            )
            if isinstance(reply, types.Error):
                self.bot.logger.warning(f"Error sending message: {reply}")
            await call.end(chat_id)

    async def end_inactive_calls(self):
        if self._lock.locked():
            self.bot.logger.warning("end_inactive_calls is already running, skipping...")
            return

        async with self._lock:
            if not await db.get_auto_end(self.bot.me.id):
                return

            active_chats = chat_cache.get_active_chats()
            if not active_chats:
                return

            self.bot.logger.debug(f"Checking {len(active_chats)} active chats...")
            semaphore = asyncio.Semaphore(4)
            tasks = [
                self._end_inactive_calls(chat_id, semaphore)
                for chat_id in active_chats
            ]
            await asyncio.gather(*tasks)

    async def leave_all(self):
        if not AUTO_LEAVE:
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
        self.scheduler.add_job(self.end_inactive_calls, CronTrigger(minute='*/1'))
        self.scheduler.add_job(self.leave_all, CronTrigger(hour=0, minute=0))
        self.scheduler.start()
        self.bot.logger.info("Scheduler started.")

    async def stop_scheduler(self):
        self.scheduler.shutdown()
        self.bot.logger.info("Scheduler stopped.")
