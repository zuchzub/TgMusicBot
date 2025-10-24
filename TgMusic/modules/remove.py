# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

from pytdbot import Client, types
from TgMusic.core import Filter, chat_cache
from TgMusic.core.admins import is_admin
from .utils.play_helpers import extract_argument


@Client.on_message(filters=Filter.command("remove"))
async def remove_song(c: Client, msg: types.Message) -> None:
    """Kuyruktaki belirli bir şarkıyı kaldırır."""
    chat_id = msg.chat_id
    if chat_id > 0:
        return None

    args = extract_argument(msg.text, enforce_digit=True)

    # Yönetici kontrolü
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("⛔ Bu işlemi yapmak için yönetici yetkisi gerekiyor.")
        return None

    if not chat_cache.is_active(chat_id):
        await msg.reply_text("⏸ Şu anda aktif bir müzik çalma bulunmuyor.")
        return None

    # Geçerli kullanım bilgisi
    if not args:
        await msg.reply_text(
            "ℹ️ <b>Kullanım:</b> <code>/remove [şarkı_numarası]</code>\n"
            "Örnek: <code>/remove 3</code>"
        )
        return None

    try:
        track_num = int(args)
    except ValueError:
        await msg.reply_text("⚠️ Lütfen geçerli bir şarkı numarası girin.")
        return None

    _queue = chat_cache.get_queue(chat_id)

    if not _queue:
        await msg.reply_text("📭 Şu anda çalma sırası boş.")
        return None

    if track_num <= 0 or track_num > len(_queue):
        await msg.reply_text(
            f"⚠️ Geçersiz numara. Lütfen 1 ile {len(_queue)} arasında bir sayı girin."
        )
        return None

    removed_track = chat_cache.remove_track(chat_id, track_num)
    reply = await msg.reply_text(
        f"✅ <b>{removed_track.name[:45]}</b> adlı şarkı {await msg.mention()} tarafından kaldırıldı."
    )

    if isinstance(reply, types.Error):
        c.logger.warning(f"Yanıt gönderilirken hata oluştu: {reply.message}")
    return None