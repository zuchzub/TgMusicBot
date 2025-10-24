#  Telif Hakkı (c) 2025 AshokShau
#  GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
#  TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

import asyncio
import time

from pytdbot import Client, types

from TgMusic.core import Filter, config, db
from TgMusic.logger import LOGGER
from TgMusic.modules.utils.play_helpers import del_msg, extract_argument

# Yayın sınırlamaları
REQUEST_LIMIT = 30
BATCH_SIZE = 400
BATCH_DELAY = 2
MAX_RETRIES = 2

# Aynı anda en fazla 30 istek gönderilmesini sağlar
semaphore = asyncio.Semaphore(REQUEST_LIMIT)
VALID_TARGETS = {"all", "users", "chats"}  # Geçerli hedef türleri


async def get_broadcast_targets(target: str) -> tuple[list[int], list[int]]:
    """Belirtilen hedef türüne göre kullanıcıları ve sohbetleri döndürür."""
    users = await db.get_all_users() if target in {"all", "users"} else []
    chats = await db.get_all_chats() if target in {"all", "chats"} else []
    return users, chats


async def send_message_with_retry(
    target_id: int, message: types.Message, is_copy: bool
) -> int:
    """Bir mesajı hedefe gönderir; hata durumunda tekrar dener."""
    for attempt in range(1, MAX_RETRIES + 1):
        async with semaphore:
            result = await (
                message.copy(target_id) if is_copy else message.forward(target_id)
            )

            if isinstance(result, types.Error):
                if result.code == 429:  # FloodWait hatası
                    retry_after = (
                        int(result.message.split("retry after ")[1])
                        if "retry after" in result.message
                        else 1
                    )
                    LOGGER.warning(
                        "[FloodWait] Deneme %s/%s: %ss bekleniyor → %s",
                        attempt,
                        MAX_RETRIES,
                        retry_after,
                        target_id,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                # Yazma izni yoksa veya kullanıcı engellemişse
                if result.code == 400 and result.message in {
                    "Have no write access to the chat",
                    "USER_IS_BLOCKED",
                    "Chat not found",
                }:
                    (
                        await db.remove_chat(target_id)
                        if target_id < 0
                        else await db.remove_user(target_id)
                    )
                    return 0

                LOGGER.warning(
                    "Mesaj gönderilemedi → %s: [%d] %s",
                    target_id,
                    result.code,
                    result.message,
                )
                return 0

            return 1  # Başarılı gönderim
    return 0  # Tüm denemeler başarısız oldu


async def broadcast_to_targets(
    targets: list[int], message: types.Message, is_copy: bool
) -> tuple[int, int]:
    """Belirtilen hedeflere toplu yayın yapar."""
    sent = failed = 0

    async def process_batch(_batch: list[int], index: int):
        results = await asyncio.gather(
            *[send_message_with_retry(tid, message, is_copy) for tid in _batch]
        )
        _batch_sent = sum(results)
        _batch_failed = len(_batch) - _batch_sent
        LOGGER.info(
            "Toplu işlem %s → Gönderilen: %s | Başarısız: %s",
            index + 1,
            _batch_sent,
            _batch_failed,
        )
        return _batch_sent, _batch_failed

    # Hedefleri 400’lük parçalara ayırır
    batches = [targets[i : i + BATCH_SIZE] for i in range(0, len(targets), BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        LOGGER.info(
            "Gönderiliyor (%s/%s) → %s hedef",
            idx + 1,
            len(batches),
            len(batch),
        )
        batch_sent, batch_failed = await process_batch(batch, idx)
        sent += batch_sent
        failed += batch_failed
        await asyncio.sleep(BATCH_DELAY)

    return sent, failed


@Client.on_message(filters=Filter.command("broadcast"))
async def broadcast(c: Client, message: types.Message) -> None:
    """Bot sahibinin tüm kullanıcı ve gruplara mesaj yayınlamasını sağlar."""
    if int(message.from_id) != config.OWNER_ID:
        await del_msg(message)
        return None

    args = extract_argument(message.text)
    if not args:
        reply = await message.reply_text(
            "Kullanım: <code>/broadcast [all|users|chats] [copy]</code>\n"
            "• <b>all</b>: Tüm kullanıcılar ve sohbetler\n"
            "• <b>users</b>: Sadece kullanıcılar\n"
            "• <b>chats</b>: Sadece gruplar/kanallar\n"
            "• <b>copy</b>: Mesajı kopya olarak gönder (iletilmiş etiketi olmadan)"
        )
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return None

    parts = args.lower().split()
    is_copy = "copy" in parts
    target = next((p for p in parts if p in VALID_TARGETS), None)

    if not target:
        reply = await message.reply_text(
            "Lütfen geçerli bir hedef belirtin: all, users veya chats."
        )
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return None

    reply = await message.getRepliedMessage() if message.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        _reply = await message.reply_text("Lütfen yayınlamak için bir mesaja yanıt verin.")
        if isinstance(_reply, types.Error):
            c.logger.warning(_reply.message)
        return None

    users, chats = await get_broadcast_targets(target)
    total_targets = len(users) + len(chats)

    if total_targets == 0:
        _reply = await message.reply_text("Yayın yapılacak kullanıcı veya sohbet bulunamadı.")
        if isinstance(_reply, types.Error):
            c.logger.warning(_reply.message)
        return None

    started = await message.reply_text(
        text=f"📣 <b>Yayın Başlatıldı!</b>\n"
        f"• Toplam Hedef: {total_targets}\n"
        f"• Kullanıcılar: {len(users)}\n"
        f"• Sohbetler: {len(chats)}\n"
        f"• Mod: {'Kopya' if is_copy else 'İletme'}",
        disable_web_page_preview=True,
    )

    if isinstance(started, types.Error):
        c.logger.warning("Yayın başlatılamadı: %s", started)
        await message.reply_text(f"Yayın başlatılamadı: {started.message}")
        return None

    start_time = time.monotonic()
    user_sent, user_failed = await broadcast_to_targets(users, reply, is_copy)
    chat_sent, chat_failed = await broadcast_to_targets(chats, reply, is_copy)
    end_time = time.monotonic()

    reply = await started.edit_text(
        text=f"✅ <b>Yayın Özeti</b>\n"
        f"• Toplam Gönderilen: {user_sent + chat_sent}\n"
        f"  ├ Kullanıcılar: {user_sent}\n"
        f"  └ Sohbetler: {chat_sent}\n"
        f"• Toplam Başarısız: {user_failed + chat_failed}\n"
        f"  ├ Kullanıcılar: {user_failed}\n"
        f"  └ Sohbetler: {chat_failed}\n"
        f"🕒 Geçen Süre: <code>{end_time - start_time:.2f} saniye</code>",
        disable_web_page_preview=True,
    )

    if isinstance(reply, types.Error):
        c.logger.warning("Yayın özeti gönderilemedi: %s", reply)
    return None