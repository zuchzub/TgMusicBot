# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

from pytdbot import Client, types

from TgMusic.core import Filter, chat_cache
from TgMusic.core.admins import is_admin
from TgMusic.modules.utils.play_helpers import extract_argument


@Client.on_message(filters=Filter.command("tekrarla"))
async def modify_loop(c: Client, msg: types.Message) -> None:
    """Şu anda çalan şarkının döngü sayısını ayarlar (0 = kapat)."""
    chat_id = msg.chat_id
    if chat_id > 0:
        return

    # Yönetici kontrolü
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("⛔ Bu komutu sadece yöneticiler kullanabilir.")
        return

    # Aktif müzik yoksa
    if not chat_cache.is_active(chat_id):
        await msg.reply_text("ℹ️ Şu anda çalan bir müzik yok.")
        return

    # Argüman kontrolü
    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text(
            "🔁 <b>Döngü Kontrolü</b>\n\n"
            "Kullanım: <code>/loop [sayı]</code>\n"
            "• <b>0</b> → Döngüyü kapatır\n"
            "• <b>1 - 10</b> → Şarkıyı belirtilen sayıda tekrarlar"
        )
        return

    loop = int(args)
    if loop < 0 or loop > 10:
        await msg.reply_text("⚠️ Döngü sayısı 0 ile 10 arasında olmalıdır.")
        return

    # Döngü sayısını kaydet
    chat_cache.set_loop_count(chat_id, loop)

    action = (
        "🔁 Döngü devre dışı bırakıldı."
        if loop == 0
        else f"🔁 Şarkı {loop} kez tekrarlanacak."
    )

    reply = await msg.reply_text(f"{action}\n🎧 Değiştiren: {await msg.mention()}")
    if isinstance(reply, types.Error):
        c.logger.warning(f"⚠️ Yanıt gönderilemedi: {reply.message}")