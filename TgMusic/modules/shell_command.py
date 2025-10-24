# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

import asyncio
import os
import uuid

from pytdbot import Client, types
from TgMusic.logger import LOGGER
from TgMusic.core import Filter, config


async def run_shell_command(cmd: str, timeout: int = 60) -> tuple[str, str, int]:
    """Terminal komutunu çalıştırır ve çıktıyı döndürür."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return "", f"⏱ Komut {timeout} saniye içinde tamamlanmadı (zaman aşımı).", -1

    return stdout.decode().strip(), stderr.decode().strip(), process.returncode


async def shellrunner(message: types.Message) -> types.Ok | types.Error | types.Message:
    """Terminal komutlarını uzaktan çalıştırır (/sh komutu)."""
    text = message.text.split(None, 1)
    if len(text) <= 1:
        reply = await message.reply_text("⚙️ Kullanım: <code>/sh [komut]</code>")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return types.Ok()

    command = text[1]

    """
    # Güvenlik kontrolü (istenirse aktif edilebilir)
    if any(blocked in command.lower() for blocked in [
        'rm -rf', 'sudo', 'dd ', 'mkfs', 'fdisk',
        ':(){:|:&};:', 'chmod 777', 'wget', 'curl'
    ]):
        return await message.reply_text("⚠️ Tehlikeli komut engellendi!")
    """

    try:
        # Birden fazla komutu sırayla çalıştır
        if "\n" in command:
            commands = [cmd.strip() for cmd in command.split("\n") if cmd.strip()]
            output_parts = []

            for cmd in commands:
                stdout, stderr, retcode = await run_shell_command(cmd)

                output_parts.append(f"<b>🚀 Komut:</b> <code>{cmd}</code>")
                if stdout:
                    output_parts.append(f"<b>📤 Çıktı:</b>\n<pre>{stdout}</pre>")
                if stderr:
                    output_parts.append(f"<b>❌ Hata:</b>\n<pre>{stderr}</pre>")
                output_parts.append(f"<b>🔢 Çıkış Kodu:</b> <code>{retcode}</code>\n")

            output = "\n".join(output_parts)
        else:
            stdout, stderr, retcode = await run_shell_command(command)

            output = f"<b>🚀 Komut:</b> <code>{command}</code>\n"
            if stdout:
                output += f"<b>📤 Çıktı:</b>\n<pre>{stdout}</pre>\n"
            if stderr:
                output += f"<b>❌ Hata:</b>\n<pre>{stderr}</pre>\n"
            output += f"<b>🔢 Çıkış Kodu:</b> <code>{retcode}</code>"

        # Boş çıktı kontrolü
        if not output.strip():
            output = "<b>📭 Herhangi bir çıktı döndürülmedi.</b>"

        # Çıktı kısa ise mesaj olarak gönder
        if len(output) <= 2000:
            return await message.reply_text(str(output), parse_mode="html")

        # Uzun çıktı — dosya olarak gönder
        filename = f"database/{uuid.uuid4().hex}.txt"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(output)

        reply = await message.reply_document(
            document=types.InputFileLocal(filename),
            caption="📁 Çıktı çok uzun olduğu için dosya olarak gönderildi:",
            disable_notification=True,
            parse_mode="html",
        )

        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)

        if os.path.exists(filename):
            os.remove(filename)

        return types.Ok()

    except Exception as e:
        return await message.reply_text(
            f"⚠️ <b>Hata oluştu:</b>\n<pre>{str(e)}</pre>", parse_mode="html"
        )


@Client.on_message(filters=Filter.command("sh"))
async def shell_command(_: Client, m: types.Message) -> None:
    """Yalnızca sahip tarafından kullanılabilen terminal komutu çalıştırıcı."""
    if int(m.from_id) != config.OWNER_ID:
        return None

    done = await shellrunner(m)
    if isinstance(done, types.Error):
        LOGGER.warning(done.message)
        return None
    return None