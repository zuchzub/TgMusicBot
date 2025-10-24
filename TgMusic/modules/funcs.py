# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

from typing import Union
from pytdbot import Client, types

from TgMusic.core import Filter, chat_cache, call, db
from TgMusic.core.admins import is_admin
from TgMusic.modules.utils.play_helpers import extract_argument


@Client.on_message(filters=Filter.command(["playtype", "setPlayType"]))
async def set_play_type(_: Client, msg: types.Message) -> None:
    """Müzik çalma modunu ayarlar."""
    chat_id = msg.chat_id
    if chat_id > 0:
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("⛔ Bu komutu yalnızca yöneticiler kullanabilir.")
        return

    play_type = extract_argument(msg.text, enforce_digit=True)
    if not play_type:
        text = (
            "🎶 <b>Kullanım:</b> <code>/setPlayType 0</code> veya <code>/setPlayType 1</code>\n\n"
            "0 ➜ Arama sonucundaki ilk şarkıyı direkt çalar.\n"
            "1 ➜ Seçim yapılabilecek bir şarkı listesi gösterir."
        )
        await msg.reply_text(text)
        return

    play_type = int(play_type)
    if play_type not in (0, 1):
        await msg.reply_text("⚠️ Geçersiz mod! Lütfen sadece 0 veya 1 değerini girin.")
        return

    await db.set_play_type(chat_id, play_type)
    await msg.reply_text(
        f"✅ <b>Çalma modu güncellendi:</b> <code>{play_type}</code>\n"
        f"{'🔁 Direkt oynatma' if play_type == 0 else '🎵 Liste seçimi modu etkin'}"
    )


async def is_admin_or_reply(msg: types.Message) -> Union[int, types.Message, types.Error]:
    """Yönetici izni ve aktif oturum kontrolü."""
    chat_id = msg.chat_id

    if not chat_cache.is_active(chat_id):
        return await msg.reply_text("ℹ️ Şu anda aktif bir müzik çalma yok 🎧")

    if not await is_admin(chat_id, msg.from_id):
        return await msg.reply_text("⛔ Bu işlemi yapmak için yönetici yetkisi gerekiyor.")

    return chat_id


async def handle_playback_action(
    c: Client, msg: types.Message, action, success_msg: str, fail_msg: str
) -> None:
    """Oynatma kontrolleri için genel işlem fonksiyonu."""
    _chat_id = await is_admin_or_reply(msg)
    if isinstance(_chat_id, types.Error):
        c.logger.warning(f"⚠️ Yönetici kontrolü başarısız: {_chat_id.message}")
        return

    if isinstance(_chat_id, types.Message):
        return

    result = await action(_chat_id)
    if isinstance(result, types.Error):
        await msg.reply_text(f"⚠️ {fail_msg}\n<code>{result.message}</code>")
        return

    await msg.reply_text(f"{success_msg}\n🎧 Talep eden: {await msg.mention()}")


@Client.on_message(filters=Filter.command("pause"))
async def pause_song(c: Client, msg: types.Message) -> None:
    """Şu anda çalan müziği duraklatır."""
    await handle_playback_action(
        c, msg, call.pause, "⏸️ Şarkı duraklatıldı.", "❌ Şarkı duraklatılamadı."
    )


@Client.on_message(filters=Filter.command("resume"))
async def resume_song(c: Client, msg: types.Message) -> None:
    """Duraklatılan müziği devam ettirir."""
    await handle_playback_action(
        c, msg, call.resume, "▶️ Müzik kaldığı yerden devam ediyor!", "❌ Devam ettirilemedi."
    )


@Client.on_message(filters=Filter.command("mute"))
async def mute_song(c: Client, msg: types.Message) -> None:
    """Müziğin sesini kapatır (sessize alır)."""
    await handle_playback_action(
        c, msg, call.mute, "🔇 Ses kapatıldı.", "❌ Ses kapatılamadı."
    )


@Client.on_message(filters=Filter.command("unmute"))
async def unmute_song(c: Client, msg: types.Message) -> None:
    """Müziğin sesini açar."""
    await handle_playback_action(
        c, msg, call.unmute, "🔊 Ses açıldı.", "❌ Ses açılamadı."
    )