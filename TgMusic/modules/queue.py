# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

from pytdbot import Client, types
from TgMusic.core import Filter, chat_cache, call
from TgMusic.modules.utils import sec_to_min


@Client.on_message(filters=Filter.command("queue"))
async def queue_info(_: Client, msg: types.Message) -> None:
    """Şu anda çalan müzik kuyruğunu detaylı şekilde gösterir."""
    if msg.chat_id > 0:
        return

    chat_id = msg.chat_id
    _queue = chat_cache.get_queue(chat_id)

    # Boş sıra kontrolü
    if not _queue:
        await msg.reply_text("📭 Şu anda sırada şarkı bulunmuyor.")
        return

    if not chat_cache.is_active(chat_id):
        await msg.reply_text("⏸ Şu anda aktif bir oynatma yok.")
        return

    chat = await msg.getChat()
    if isinstance(chat, types.Error):
        await msg.reply_text(
            f"⚠️ <b>Hata:</b> Sohbet bilgileri alınamadı\n<code>{chat.message}</code>"
        )
        return

    current_song = _queue[0]
    text = [
        f"<b>🎧 {chat.title} - Müzik Sırası</b>",
        "",
        "<b>▶️ Şu Anda Çalıyor:</b>",
        f"├ <b>Şarkı:</b> <code>{current_song.name[:45]}</code>",
        f"├ <b>İsteyen:</b> {current_song.user}",
        f"├ <b>Süre:</b> {sec_to_min(current_song.duration)} dk",
        f"├ <b>Döngü:</b> {'🔁 Açık' if current_song.loop else '➡️ Kapalı'}",
        f"└ <b>İlerleme:</b> {sec_to_min(await call.played_time(chat.id))} dk",
    ]

    # Sonraki şarkılar
    if len(_queue) > 1:
        text.extend(["", f"<b>⏭ Sıradakiler ({len(_queue) - 1}):</b>"])
        text.extend(
            f"{i}. <code>{song.name[:45]}</code> | {sec_to_min(song.duration)} dk"
            for i, song in enumerate(_queue[1:11], 1)
        )
        if len(_queue) > 11:
            text.append(f"...ve {len(_queue) - 11} şarkı daha 🎶")

    text.append(f"\n<b>📊 Toplam:</b> {len(_queue)} şarkı sırada 🎵")

    # Uzun metinler için kısaltma
    formatted_text = "\n".join(text)
    if len(formatted_text) > 4096:
        formatted_text = "\n".join(
            [
                f"<b>🎧 {chat.title} - Müzik Sırası</b>",
                "",
                "<b>▶️ Şu Anda Çalıyor:</b>",
                f"├ <code>{current_song.name[:45]}</code>",
                f"└ {sec_to_min(await call.played_time(chat.id))}/{sec_to_min(current_song.duration)} dk",
                "",
                f"<b>📊 Toplam:</b> {len(_queue)} şarkı sırada 🎶",
            ]
        )

    await msg.reply_text(text=formatted_text, disable_web_page_preview=True)