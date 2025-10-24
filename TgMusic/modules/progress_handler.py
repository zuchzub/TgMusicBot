# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

import math
import time
from pytdbot import Client, types
from TgMusic.core import tg
from TgMusic.logger import LOGGER
from TgMusic.core.admins import is_admin

download_progress = {}


def _format_bytes(size: int) -> str:
    """Bayt değerini insan okunabilir bir biçime dönüştürür."""
    if size < 1024:
        return f"{size} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"


def _format_time(seconds: float) -> str:
    """Saniyeyi okunabilir süre formatına dönüştürür."""
    if seconds < 60:
        return f"{int(seconds)} sn"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)} dk {int(seconds)} sn"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)} sa {int(minutes)} dk"


def _create_progress_bar(percentage: int, length: int = 10) -> str:
    """Yüzdelik orana göre ilerleme çubuğu oluşturur."""
    filled = round(length * percentage / 100)
    return "⬢" * filled + "⬡" * (length - filled)


def _calculate_update_interval(file_size: int, speed: float) -> float:
    """Güncelleme aralığını dosya boyutu ve hıza göre hesaplar."""
    if file_size < 5 * 1024 * 1024:
        base = 1.0
    else:
        scale = min(math.log10(file_size / (5 * 1024 * 1024)), 2)
        base = 1.0 + scale * 2.0

    speed_mod = max(0.5, 2.0 - (speed / (5 * 1024 * 1024))) if speed > 1024 * 1024 else 1.0
    return min(max(base * speed_mod, 1.0), 5.0)


def _get_button(unique_id: str) -> types.ReplyMarkupInlineKeyboard:
    """İndirilen dosya için 'İndirmeyi Durdur' butonu oluşturur."""
    return types.ReplyMarkupInlineKeyboard(
        [
            [
                types.InlineKeyboardButton(
                    text="✗ İndirmeyi Durdur",
                    type=types.InlineKeyboardButtonTypeCallback(
                        f"play_c_{unique_id}".encode()
                    ),
                )
            ]
        ]
    )


def _should_update(progress: dict, now: float, completed: bool) -> bool:
    """İlerleme güncellemesi gerekip gerekmediğini kontrol eder."""
    return now >= progress["next_update"] or completed


def _build_progress_text(filename: str, total: int, downloaded: int, speed: float) -> str:
    """İndirme işleminin ilerleme mesajını oluşturur."""
    percentage = min(100, int((downloaded / total) * 100))
    eta = int((total - downloaded) / speed) if speed > 0 else -1
    return (
        f"📥 <b>İndiriliyor:</b> <code>{filename}</code>\n"
        f"💾 <b>Boyut:</b> {_format_bytes(total)}\n"
        f"📊 <b>İlerleme:</b> {percentage}% {_create_progress_bar(percentage)}\n"
        f"🚀 <b>Hız:</b> {_format_bytes(int(speed))}/s\n"
        f"⏳ <b>Kalan Süre:</b> {_format_time(eta) if eta >= 0 else 'Hesaplanıyor...'}"
    )


def _build_complete_text(filename: str, total: int, duration: float) -> str:
    """İndirme tamamlandığında gönderilen mesajı oluşturur."""
    avg_speed = total / max(duration, 1e-6)
    return (
        f"✅ <b>İndirme Tamamlandı:</b> <code>{filename}</code>\n"
        f"💾 <b>Boyut:</b> {_format_bytes(total)}\n"
        f"⏱ <b>Süre:</b> {_format_time(duration)}\n"
        f"⚡ <b>Ortalama Hız:</b> {_format_bytes(int(avg_speed))}/s"
    )


@Client.on_updateFile()
async def update_file(client: Client, update: types.UpdateFile):
    """Dosya indirme ilerleme güncellemelerini yönetir."""
    file = update.file
    unique_id = file.remote.unique_id
    meta = tg.get_cached_metadata(unique_id)
    if not meta:
        return

    chat_id = meta["chat_id"]
    filename = meta["filename"]
    message_id = meta["message_id"]
    file_id = file.id
    now = time.time()

    total = file.size or 1
    downloaded = file.local.downloaded_size

    if file_id not in download_progress:
        download_progress[file_id] = {
            "start_time": now,
            "last_update": now,
            "last_size": downloaded,
            "next_update": now + 1.0,
            "last_speed": 0,
        }

    progress = download_progress[file_id]

    if not _should_update(progress, now, file.local.is_downloading_completed):
        return

    elapsed = now - progress["last_update"]
    delta = downloaded - progress["last_size"]
    speed = delta / elapsed if elapsed > 0 else 0
    interval = _calculate_update_interval(total, speed)

    progress.update(
        {
            "next_update": now + interval,
            "last_update": now,
            "last_size": downloaded,
            "last_speed": speed,
        }
    )

    button_markup = _get_button(unique_id)

    if not file.local.is_downloading_completed:
        text = _build_progress_text(filename, total, downloaded, speed)
        parsed = await client.parseTextEntities(text, types.TextParseModeHTML())
        edit = await client.editMessageText(
            chat_id, message_id, button_markup, types.InputMessageText(parsed)
        )
        if isinstance(edit, types.Error):
            LOGGER.error("İndirme ilerlemesi güncellenemedi: %s", edit)
        return

    # Tamamlandığında
    duration = now - progress["start_time"]
    complete_text = _build_complete_text(filename, total, duration)
    parsed = await client.parseTextEntities(complete_text, types.TextParseModeHTML())
    done = await client.editMessageText(
        chat_id, message_id, button_markup, types.InputMessageText(parsed)
    )
    if isinstance(done, types.Error):
        LOGGER.error("İndirme tamamlandı mesajı gönderilemedi: %s", done)

    download_progress.pop(file_id, None)


async def _handle_play_c_data(
    data: str,
    message: types.UpdateNewCallbackQuery,
    chat_id: int,
    user_id: int,
    user_name: str,
    c: Client,
):
    """İndirme iptali butonunu yönetir."""
    if not await is_admin(chat_id, user_id):
        await message.answer("⚠️ Bu işlemi yalnızca yöneticiler yapabilir.", show_alert=True)
        return

    _, _, file_id = data.split("_", 2)
    meta = tg.get_cached_metadata(file_id)
    if not meta:
        await message.answer("Bu dosya zaten indirildi.", show_alert=True)
        return

    file_info = await c.getRemoteFile(meta["remote_file_id"])
    if isinstance(file_info, types.Error):
        await message.answer("Dosya bilgisi alınamadı.", show_alert=True)
        LOGGER.error("Dosya bilgisi alınamadı: %s", file_info.message)
        return

    ok = await c.cancelDownloadFile(file_info.id)
    if isinstance(ok, types.Error):
        await message.answer(f"İndirme iptal edilemedi. {ok.message}", show_alert=True)
        return

    await message.answer("İndirme iptal edildi.", show_alert=True)
    await message.edit_message_text(f"🚫 İndirme iptal edildi.\n👤 Talep eden: {user_name}")