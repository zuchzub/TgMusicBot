# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

import re
from pytdbot import Client, types
from TgMusic.core import Filter, chat_cache, call
from TgMusic.core.admins import is_admin


def extract_number(text: str) -> float | None:
    """Metinden sayısal bir değer çıkarır."""
    match = re.search(r"[-+]?\d*\.?\d+", text)
    return float(match.group()) if match else None


@Client.on_message(filters=Filter.command(["speed", "cspeed"]))
async def change_speed(_: Client, msg: types.Message) -> None:
    """Geçerli parçanın oynatma hızını değiştirir."""
    chat_id = msg.chat_id
    if chat_id > 0:
        return

    # Yönetici kontrolü
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("⛔ Bu komutu yalnızca yöneticiler kullanabilir.")
        return

    args = extract_number(msg.text)
    if args is None:
        await msg.reply_text(
            "ℹ️ <b>Kullanım:</b> <code>/speed [değer]</code>\n"
            "Örnek: <code>/speed 1.5</code> → 1.5x hız\n"
            "Aralık: 0.5x ile 4.0x arası"
        )
        return

    if not chat_cache.is_active(chat_id):
        await msg.reply_text("⏸ Şu anda çalan bir parça yok.")
        return

    speed = round(float(args), 2)
    if speed < 0.5 or speed > 4.0:
        await msg.reply_text("⚠️ Hız değeri 0.5x ile 4.0x arasında olmalıdır.")
        return

    _change_speed = await call.speed_change(chat_id, speed)
    if isinstance(_change_speed, types.Error):
        await msg.reply_text(f"⚠️ <b>Hata:</b> {_change_speed.message}")
        return

    await msg.reply_text(
        f"🎚️ Oynatma hızı <b>{speed}x</b> olarak ayarlandı.\n"
        f"🎵 Ayarlayan: {await msg.mention()}"
    )