# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

from pytdbot import Client, types
from TgMusic.core import Filter, call
from .funcs import is_admin_or_reply


@Client.on_message(filters=Filter.command(["stop", "son"]))
async def stop_song(c: Client, msg: types.Message) -> None:
    """Müziği durdurur ve sırayı temizler."""
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Error):
        c.logger.warning(f"Yönetici kontrol hatası: {chat_id.message}")
        return None

    if isinstance(chat_id, types.Message):
        return None

    _end = await call.end(chat_id)
    if isinstance(_end, types.Error):
        await msg.reply_text(f"⚠️ <b>Hata:</b> {_end.message}")
        return None

    await msg.reply_text(
        f"⏹️ Oynatma {await msg.mention()} tarafından durduruldu.\n"
        f"🧹 Müzik sırası başarıyla temizlendi!"
    )
    return None