# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

from pytdbot import Client, types

from TgMusic.core import Filter, db, is_owner
from TgMusic.logger import LOGGER
from TgMusic.modules.utils.play_helpers import extract_argument


@Client.on_message(filters=Filter.command(["buttons"]))
async def buttons(_: Client, msg: types.Message) -> None:
    """Buton kontrol sistemini aç/kapat."""
    chat_id = msg.chat_id
    if chat_id > 0:
        reply = await msg.reply_text("❌ Bu komut yalnızca gruplarda kullanılabilir.")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    if not await is_owner(chat_id, msg.from_id):
        reply = await msg.reply_text("⛔ Bu işlemi yalnızca **grup sahibi** gerçekleştirebilir.")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    current = await db.get_buttons_status(chat_id)
    args = extract_argument(msg.text)

    if not args:
        status = "aktif ✅" if current else "devre dışı ❌"
        reply = await msg.reply_text(
            f"⚙️ <b>Buton Kontrol Durumu:</b> {status}\n\n"
            "Kullanım: <code>/buttons [on|off|enable|disable]</code>"
        )
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    arg = args.lower()
    if arg in ["on", "enable"]:
        await db.set_buttons_status(chat_id, True)
        reply = await msg.reply_text("✅ Butonlar etkinleştirildi! Artık kontrol butonları aktif 🎵")
    elif arg in ["off", "disable"]:
        await db.set_buttons_status(chat_id, False)
        reply = await msg.reply_text("❌ Butonlar devre dışı bırakıldı. Kontrol butonları artık gizlenecek.")
    else:
        reply = await msg.reply_text(
            "⚠️ Hatalı kullanım!\n"
            "Doğru kullanım: <code>/buttons [enable|disable|on|off]</code>"
        )
    if isinstance(reply, types.Error):
        LOGGER.warning(reply.message)


@Client.on_message(filters=Filter.command(["thumbnail", "thumb"]))
async def thumbnail(_: Client, msg: types.Message) -> None:
    """Küçük resim (thumbnail) ayarlarını aç/kapat."""
    chat_id = msg.chat_id
    if chat_id > 0:
        reply = await msg.reply_text("❌ Bu komut yalnızca gruplarda kullanılabilir.")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    if not await is_owner(chat_id, msg.from_id):
        reply = await msg.reply_text("⛔ Bu işlemi yalnızca **grup sahibi** gerçekleştirebilir.")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    current = await db.get_thumbnail_status(chat_id)
    args = extract_argument(msg.text)

    if not args:
        status = "aktif ✅" if current else "devre dışı ❌"
        reply = await msg.reply_text(
            f"🖼️ <b>Küçük Resim Durumu:</b> {status}\n\n"
            "Kullanım: <code>/thumbnail [on|off|enable|disable]</code>"
        )
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    arg = args.lower()
    if arg in ["on", "enable"]:
        await db.set_thumbnail_status(chat_id, True)
        reply = await msg.reply_text("✅ Küçük resimler **etkinleştirildi!** Artık oynatma görselleri gösterilecek 🖼️")
    elif arg in ["off", "disable"]:
        await db.set_thumbnail_status(chat_id, False)
        reply = await msg.reply_text("❌ Küçük resimler **devre dışı bırakıldı.** Görseller gizlenecek.")
    else:
        reply = await msg.reply_text(
            "⚠️ Hatalı kullanım!\n"
            "Doğru kullanım: <code>/thumbnail [enable|disable|on|off]</code>"
        )
    if isinstance(reply, types.Error):
        LOGGER.warning(reply.message)