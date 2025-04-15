#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import time

from pytdbot import Client, types

from config import OWNER_ID
from src import db
from src.logger import LOGGER
from src.modules.utils import Filter
from src.modules.utils.play_helpers import del_msg, extract_argument

REQUEST_LIMIT = 50
BATCH_SIZE = 500
BATCH_DELAY = 2
MAX_RETRIES = 3

semaphore = asyncio.Semaphore(REQUEST_LIMIT)
VALID_TARGETS = {"all", "users", "chats"}


async def get_broadcast_targets(target: str) -> tuple[list[int], list[int]]:
    users = await db.get_all_users() if target in {"all", "users"} else []
    chats = await db.get_all_chats() if target in {"all", "chats"} else []
    return users, chats


async def send_message_with_retry(
    target_id: int, message: types.Message, is_copy: bool
) -> int:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                result = await (
                    message.copy(target_id) if is_copy else message.forward(target_id)
                )

            if isinstance(result, types.Error):
                if result.code == 429:
                    retry_after = (
                        int(result.message.split("retry after ")[1])
                        if "retry after" in result.message
                        else 2
                    )
                    LOGGER.warning(
                        "[FloodWait] Retry %s/%s in %ss for %s",
                        attempt,
                        MAX_RETRIES,
                        retry_after,
                        target_id,
                    )
                    await asyncio.sleep(retry_after)
                    continue
                elif result.code == 400:
                    LOGGER.warning("Bad request for %s: %s", target_id, result.message)
                    return 0
                return 0

            return 1

        except Exception as e:
            LOGGER.error("[Error] %s: %s", target_id, e)
            await asyncio.sleep(2)

    return 0


async def broadcast_to_targets(
    targets: list[int], message: types.Message, is_copy: bool
) -> tuple[int, int]:
    sent = failed = 0

    async def process_batch(_batch: list[int], index: int):
        results = await asyncio.gather(
            *[send_message_with_retry(tid, message, is_copy) for tid in _batch]
        )
        _batch_sent = sum(results)
        _batch_failed = len(_batch) - _batch_sent
        LOGGER.info(
            "Batch %s sent: %s, failed: %s", index + 1, _batch_sent, _batch_failed
        )
        return _batch_sent, _batch_failed

    batches = [targets[i : i + BATCH_SIZE] for i in range(0, len(targets), BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        LOGGER.info(
            "Sending batch %s/%s (targets: %s)", idx + 1, len(batches), len(batch)
        )
        batch_sent, batch_failed = await process_batch(batch, idx)
        sent += batch_sent
        failed += batch_failed
        await asyncio.sleep(BATCH_DELAY)

    return sent, failed


@Client.on_message(filters=Filter.command("broadcast"))
async def broadcast(_: Client, message: types.Message):
    if int(message.from_id) != OWNER_ID:
        await del_msg(message)
        return

    args = extract_argument(message.text)
    if not args:
        return await message.reply_text(
            "Usage: <code>/broadcast [all|users|chats] [copy]</code>\n"
            "• <b>all</b>: All users and chats\n"
            "• <b>users</b>: Only users\n"
            "• <b>chats</b>: Only groups/channels\n"
            "• <b>copy</b>: Send as copy (no forward tag)"
        )

    parts = args.lower().split()
    is_copy = "copy" in parts
    target = next((p for p in parts if p in VALID_TARGETS), None)

    if not target:
        return await message.reply_text(
            "Please specify a valid target: all, users, or chats."
        )

    reply = await message.getRepliedMessage() if message.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        return await message.reply_text("Please reply to a message to broadcast.")

    users, chats = await get_broadcast_targets(target)
    total_targets = len(users) + len(chats)

    if total_targets == 0:
        return await message.reply_text("No users or chats to broadcast to.")

    started = await message.reply_text(
        text=f"📣 Starting broadcast to {total_targets} target(s)...\n"
        f"• Users: {len(users)}\n"
        f"• Chats: {len(chats)}\n"
        f"• Mode: {'Copy' if is_copy else 'Forward'}",
        disable_web_page_preview=True,
    )

    if isinstance(started, types.Error):
        LOGGER.warning("Error starting broadcast: %s", started)
        return

    start_time = time.monotonic()

    user_sent, user_failed = await broadcast_to_targets(users, reply, is_copy)
    chat_sent, chat_failed = await broadcast_to_targets(chats, reply, is_copy)

    end_time = time.monotonic()

    await started.edit_text(
        text=f"✅ <b>Broadcast Summary</b>\n"
        f"• Total Sent: {user_sent + chat_sent}\n"
        f"  - Users: {user_sent}\n"
        f"  - Chats: {chat_sent}\n"
        f"• Total Failed: {user_failed + chat_failed}\n"
        f"  - Users: {user_failed}\n"
        f"  - Chats: {chat_failed}\n"
        f"🕒 Time Taken: <code>{end_time - start_time:.2f} sec</code>",
        disable_web_page_preview=True,
    )
