# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

from pytdbot import Client, types
from TgMusic.core import Filter, chat_cache, call
from TgMusic.core.admins import is_admin
from .utils import sec_to_min
from .utils.play_helpers import extract_argument


@Client.on_message(filters=Filter.command("seek"))
async def seek_song(_: Client, msg: types.Message) -> None:
    """Çalan şarkının belirli bir saniyesine atlamayı sağlar."""
    chat_id = msg.chat_id

    # Özel sohbetlerde devre dışı
    if chat_id > 0:
        return

    # Yönetici kontrolü
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("⛔ Bu komutu yalnızca yöneticiler kullanabilir.")
        return

    curr_song = chat_cache.get_playing_track(chat_id)
    if not curr_song:
        await msg.reply_text("⏸ Şu anda çalan bir parça yok.")
        return

    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text(
            "ℹ️ <b>Kullanım:</b> <code>/seek [saniye]</code>\n"
            "Örnek: <code>/seek 30</code> → 30 saniye ileri sarar."
        )
        return

    try:
        seek_time = int(args)
    except ValueError:
        await msg.reply_text("⚠️ Lütfen geçerli bir saniye değeri girin.")
        return

    if seek_time < 0:
        await msg.reply_text("⚠️ Pozitif bir sayı girmen gerekiyor.")
        return

    if seek_time < 20:
        await msg.reply_text("⚠️ Minimum ileri sarma süresi 20 saniyedir.")
        return

    curr_dur = await call.played_time(chat_id)
    if isinstance(curr_dur, types.Error):
        await msg.reply_text(f"⚠️ <b>Hata:</b> {curr_dur.message}")
        return

    seek_to = curr_dur + seek_time
    if seek_to >= curr_song.duration:
        max_duration = sec_to_min(curr_song.duration)
        await msg.reply_text(f"⚠️ Şarkı süresini aşıyorsun ({max_duration}).")
        return

    _seek = await call.seek_stream(
        chat_id,
        curr_song.file_path,
        seek_to,
        curr_song.duration,
        curr_song.is_video,
    )
    if isinstance(_seek, types.Error):
        await msg.reply_text(f"⚠️ <b>Hata:</b> {_seek.message}")
        return

    await msg.reply_text(
        f"⏩ {seek_time} saniye ileri sarıldı. ({await msg.mention()})\n"
        f"🎵 Şu an: {sec_to_min(seek_to)}/{sec_to_min(curr_song.duration)}"
    )