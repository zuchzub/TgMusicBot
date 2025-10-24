from pytdbot import Client, types

from TgMusic.core import Filter, chat_cache
from TgMusic.core.admins import is_admin


@Client.on_message(filters=Filter.command("clear"))
async def clear_queue(c: Client, msg: types.Message) -> None:
    """Müzik kuyruğunu temizler."""
    chat_id = msg.chat_id

    # Komut sadece gruplarda çalışır
    if chat_id > 0:
        return None

    # Yönetici kontrolü
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("⛔ Bu işlemi yapmak için yönetici yetkisi gerekiyor.")
        return None

    # Aktif oynatma yoksa
    if not chat_cache.is_active(chat_id):
        await msg.reply_text("ℹ️ Şu anda aktif bir müzik çalma yok.")
        return None

    # Sıra zaten boşsa
    if not chat_cache.get_queue(chat_id):
        await msg.reply_text("ℹ️ Şarkı listesi zaten boş 🎶")
        return None

    # Kuyruğu temizle
    chat_cache.clear_chat(chat_id)
    reply = await msg.reply_text(f"✅ 🎧 Müzik sırası {await msg.mention()} tarafından temizlendi!")
    if isinstance(reply, types.Error):
        c.logger.warning(f"Yanıt gönderilirken hata oluştu: {reply}")
    return None