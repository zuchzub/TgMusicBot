# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

import asyncio
import os
import shutil
import sys
import uuid
from os import execvp
from pytdbot import Client, types

from TgMusic.core import chat_cache, call, Filter, config
from TgMusic.logger import LOGGER
from TgMusic.modules.utils.play_helpers import del_msg


def is_docker():
    """Docker ortamında çalışıp çalışmadığını kontrol eder."""
    if os.path.exists("/.dockerenv"):
        return True
    if os.path.isfile("/proc/1/cgroup"):
        try:
            with open("/proc/1/cgroup", "r") as f:
                return "docker" in f.read()
        except Exception as e:
            LOGGER.warning("Docker kontrolü başarısız: %s", e)
            return False
    return False


@Client.on_message(filters=Filter.command(["update", "restart"]))
async def update(c: Client, message: types.Message) -> None:
    """Botu güncelle veya yeniden başlat."""
    if message.from_id not in config.DEVS:
        await del_msg(message)
        return

    command = message.text.strip().split()[0].lstrip("/")
    msg = await message.reply_text(
        f"{'🔄 Güncelleniyor ve ' if command == 'update' else ''}♻️ Bot yeniden başlatılıyor..."
    )

    # ──────────────── GÜNCELLEME ────────────────
    if command == "update":
        if not os.path.exists(".git"):
            await msg.edit_text("⚠️ Bu sürüm güncellemeyi desteklemiyor (.git dizini bulunamadı).")
            return

        git_path = shutil.which("git") or "/usr/bin/git"
        if not os.path.isfile(git_path):
            await msg.edit_text("❌ Git sistemde yüklü değil.")
            return

        try:
            proc = await asyncio.create_subprocess_exec(
                git_path,
                "pull",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode().strip()

            if proc.returncode != 0:
                if "Permission denied" in output or "Authentication failed" in output:
                    await msg.edit_text(
                        "❌ Güncelleme başarısız: Özel depo erişimi reddedildi.\n"
                        "SSH veya token kimlik bilgilerini kontrol et."
                    )
                else:
                    await msg.edit_text(f"⚠️ Git hatası:\n<pre>{output}</pre>")
                return

            if "Already up to date." in output:
                await msg.edit_text("✅ Bot zaten en güncel sürümde.")
                return

            if len(output) > 4096:
                filename = f"database/{uuid.uuid4().hex}.txt"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(output)

                await msg.reply_document(
                    document=types.InputFileLocal(filename),
                    caption="<b>🔍 Güncelleme Günlüğü:</b>",
                    parse_mode="html",
                    disable_notification=True,
                )
                os.remove(filename)
            else:
                await msg.edit_text(
                    f"✅ <b>Bot başarıyla güncellendi!</b>\n\n<b>📦 Güncelleme Çıktısı:</b>\n<pre>{output}</pre>"
                )

        except Exception as e:
            LOGGER.error("Beklenmedik güncelleme hatası: %s", e)
            await msg.edit_text(f"⚠️ Güncelleme hatası: {e}")
            return

    # ──────────────── VC Temizliği ────────────────
    if active_vc := chat_cache.get_active_chats():
        for chat_id in active_vc:
            await call.end(chat_id)
            await c.sendTextMessage(
                chat_id,
                "🔧 <b>Bakım Zamanı!</b>\n\n"
                "Bot şu anda yeni özellikler için güncelleniyor veya yeniden başlatılıyor.\n"
                "🎶 Müzik çalma işlemi geçici olarak durduruldu.\n"
                "⏳ Lütfen birkaç saniye sonra tekrar deneyin.",
                parse_mode="html",
            )
            await asyncio.sleep(0.5)

    await msg.edit_text("♻️ Yeniden başlatma işlemi başlatılıyor...")

    # ──────────────── YENİDEN BAŞLAT ────────────────
    if is_docker():
        await msg.edit_text("🚢 Docker ortamı algılandı — süreç Docker tarafından yeniden başlatılacak.")
        sys.exit(0)
    else:
        tgmusic_path = shutil.which("tgmusic")
        if not tgmusic_path:
            await msg.edit_text("❌ 'tgmusic' komutu PATH içinde bulunamadı.")
            return
        execvp("tgmusic", ["tgmusic"])