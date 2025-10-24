# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

from pytdbot import Client, types
from TgMusic.core import Filter, call
from .funcs import is_admin_or_reply
from .utils.play_helpers import extract_argument


@Client.on_message(filters=Filter.command(["volume", "cvolume"]))
async def volume(c: Client, msg: types.Message) -> None:
    """Ses düzeyini ayarlar (1-200%)."""
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Error):
        c.logger.warning(f"⚠️ Yönetici kontrolü başarısız: {chat_id.message}")
        return None

    if isinstance(chat_id, types.Message):
        return None

    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text(
            "🔊 <b>Ses Kontrolü</b>\n\n"
            "Kullanım: <code>/volume [1-200]</code>\n"
            "Örnek: <code>/volume 80</code> → Ses %80\n"
            "Sessize almak için: <code>/volume 0</code>"
        )
        return None

    try:
        vol_int = int(args)
    except ValueError:
        await msg.reply_text("⚠️ Lütfen 1 ile 200 arasında geçerli bir sayı girin.")
        return None

    if vol_int == 0:
        await msg.reply_text(f"🔇 Ses {await msg.mention()} tarafından kapatıldı.")
        return None

    if not 1 <= vol_int <= 200:
        await msg.reply_text("⚠️ Ses seviyesi 1 ile 200 arasında olmalıdır.")
        return None

    done = await call.change_volume(chat_id, vol_int)
    if isinstance(done, types.Error):
        await msg.reply_text(f"⚠️ <b>Hata:</b> {done.message}")
        return None

    await msg.reply_text(
        f"🔊 Ses seviyesi {await msg.mention()} tarafından <b>%{vol_int}</b> olarak ayarlandı."
    )
    return None