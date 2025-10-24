# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

import inspect
import io
import os
import platform
import re
import socket
import sys
import traceback
import uuid
from datetime import datetime, timedelta
from html import escape
from sys import version as pyver
from typing import Any, Optional, Tuple, Union

import psutil
from meval import meval
from ntgcalls import __version__ as ntgver
from pyrogram import __version__ as pyrover
from pytdbot import Client, types
from pytdbot import __version__ as py_td_ver
from pytgcalls import __version__ as pytgver

from TgMusic import StartTime
from TgMusic.core import Filter, chat_cache, config, call, db
from TgMusic.modules.utils.play_helpers import del_msg, extract_argument


def format_exception(
    exp: BaseException, tb: Optional[list[traceback.FrameSummary]] = None
) -> str:
    """Python hata izini (traceback) okunabilir biçimde düzenler."""
    if tb is None:
        tb = traceback.extract_tb(exp.__traceback__)

    cwd = os.getcwd()
    for frame in tb:
        if cwd in frame.filename:
            frame.filename = os.path.relpath(frame.filename)

    stack = "".join(traceback.format_list(tb))
    msg = str(exp)
    if msg:
        msg = f": {msg}"

    return f"Traceback (most recent call last):\n{stack}{type(exp).__name__}{msg}"


@Client.on_message(filters=Filter.command("eval"))
async def exec_eval(c: Client, m: types.Message) -> None:
    """Python kodlarını doğrudan Telegram üzerinden çalıştırır (yalnızca bot sahibine özel)."""
    if int(m.from_id) != config.OWNER_ID:
        return None

    text = m.text.split(None, 1)
    if len(text) <= 1:
        reply = await m.reply_text("Kullanım: <code>/eval &lt;kod&gt;</code>")
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return None

    code = text[1]
    out_buf = io.StringIO()

    async def _eval() -> Tuple[str, Optional[str]]:
        async def send(*args: Any, **kwargs: Any):
            return await m.reply_text(*args, **kwargs)

        def _print(*args: Any, **kwargs: Any) -> None:
            if "file" not in kwargs:
                kwargs["file"] = out_buf
            print(*args, **kwargs)

        eval_vars = {
            "loop": c.loop,
            "client": c,
            "stdout": out_buf,
            "c": c,
            "m": m,
            "msg": m,
            "types": types,
            "send": send,
            "print": _print,
            "inspect": inspect,
            "os": os,
            "re": re,
            "sys": sys,
            "traceback": traceback,
            "uuid": uuid,
            "io": io,
            "db": db,
            "call": call,
        }

        try:
            return "", await meval(code, globals(), **eval_vars)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            first_snip_idx = next(
                (i for i, frame in enumerate(tb) if frame.filename == "<string>" or frame.filename.endswith("ast.py")),
                -1,
            )

            if first_snip_idx == -1:
                raise e

            stripped_tb = tb[first_snip_idx:]
            formatted_tb = format_exception(e, tb=stripped_tb)
            return "⚠️ Hata:\n\n", formatted_tb

    prefix, result = await _eval()
    if not out_buf.getvalue() or result is not None:
        print(result, file=out_buf)

    out = out_buf.getvalue().rstrip()
    result = f"""{prefix}<b>🔹 Kod:</b>
<pre language="python">{escape(code)}</pre>
<b>🔸 Sonuç:</b>
<pre language="python">{escape(out)}</pre>"""

    if len(result) > 2000:
        filename = f"database/{uuid.uuid4().hex}.txt"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(out)

        caption = f"{prefix}<b>🔹 Kod:</b>\n<pre language='python'>{escape(code)}</pre>"
        reply = await m.reply_document(
            document=types.InputFileLocal(filename),
            caption=caption,
            disable_notification=True,
            parse_mode="html",
        )
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        os.remove(filename)
        return None

    reply = await m.reply_text(str(result), parse_mode="html")
    if isinstance(reply, types.Error):
        c.logger.warning(reply.message)


@Client.on_message(filters=Filter.command("stats"))
async def sys_stats(client: Client, message: types.Message) -> None:
    """Botun sistem durumu ve kaynak kullanımını gösterir (CPU, RAM, Disk, Ağ, Versiyonlar)."""
    if message.from_id not in config.DEVS:
        await del_msg(message)
        return None

    sys_msg = await message.reply_text("📊 Sistem istatistikleri toplanıyor...")
    if isinstance(sys_msg, types.Error):
        client.logger.warning(sys_msg.message)

    # Sistem Bilgileri
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    mac_address = ":".join(re.findall("..", f"{uuid.getnode():012x}"))
    architecture = platform.machine()
    system = platform.system()
    release = platform.release()
    processor = platform.processor() or "Bilinmiyor"

    # Donanım Bilgileri
    ram = psutil.virtual_memory()
    cores_physical = psutil.cpu_count(logical=False)
    cores_total = psutil.cpu_count(logical=True)

    try:
        cpu_freq = psutil.cpu_freq()
        cpu_freq_str = (
            f"{cpu_freq.current / 1000:.2f} GHz"
            if cpu_freq.current >= 1000
            else f"{cpu_freq.current:.2f} MHz"
        )
        if cpu_freq.max:
            cpu_freq_str += f" (Maks: {cpu_freq.max / 1000:.2f} GHz)"
    except Exception as e:
        client.logger.warning("CPU frekansı alınamadı: %s", e)
        cpu_freq_str = "Ulaşılamıyor"

    # Disk Bilgileri
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()

    # Ağ Bilgileri
    net_io = psutil.net_io_counters()
    net_if = psutil.net_if_addrs()

    # Çalışma Süresi
    uptime = timedelta(seconds=int((datetime.now() - StartTime).total_seconds()))
    load_avg = ", ".join([f"{x:.2f}" for x in psutil.getloadavg()]) if hasattr(psutil, "getloadavg") else "N/A"
    cpu_percent = psutil.cpu_percent(interval=1)

    # Veritabanı Bilgisi
    chats = len(await db.get_all_chats())
    users = len(await db.get_all_users())

    def format_bytes(size):
        for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PiB"

    response = f"""
<b>⚙️ {client.me.first_name} Sistem Bilgileri</b>
━━━━━━━━━━━━━━━━━━━━
<b>🕒 Çalışma Süresi:</b> <code>{uptime}</code>
<b>📈 Yük Ortalaması:</b> <code>{load_avg}</code>
<b>🧠 CPU Kullanımı:</b> <code>{cpu_percent}%</code>

<b>💬 Veritabanı:</b>
• Sohbetler: <code>{chats:,}</code>
• Kullanıcılar: <code>{users:,}</code>

<b>📦 Yazılım Sürümleri:</b>
• Python: <code>{pyver.split()[0]}</code>
• Pyrogram: <code>{pyrover}</code>
• PyTgCalls: <code>{pytgver}</code>
• NTgCalls: <code>{ntgver}</code>
• PyTdBot: <code>{py_td_ver}</code>

<b>🖥️ Sistem Bilgisi:</b>
• Sistem: <code>{system} {release}</code>
• Mimari: <code>{architecture}</code>
• İşlemci: <code>{processor}</code>
• Hostname: <code>{hostname}</code>
• IP Adresi: <tg-spoiler>{ip_address}</tg-spoiler>
• MAC: <code>{mac_address}</code>

<b>💾 Bellek:</b>
• RAM: <code>{ram.used / (1024 ** 3):.2f} / {ram.total / (1024 ** 3):.2f} GiB ({ram.percent}%)</code>

<b>🔧 CPU:</b>
• Çekirdek: <code>{cores_physical} fiziksel, {cores_total} mantıksal</code>
• Frekans: <code>{cpu_freq_str}</code>

<b>💽 Disk:</b>
• Toplam: <code>{disk.total / (1024 ** 3):.2f} GiB</code>
• Kullanılan: <code>{disk.used / (1024 ** 3):.2f} GiB ({disk.percent}%)</code>
• Boş: <code>{disk.free / (1024 ** 3):.2f} GiB</code>
• G/Ç: <code>Okuma: {format_bytes(disk_io.read_bytes)} | Yazma: {format_bytes(disk_io.write_bytes)}</code>

<b>🌐 Ağ:</b>
• Gönderilen: <code>{format_bytes(net_io.bytes_sent)}</code>
• Alınan: <code>{format_bytes(net_io.bytes_recv)}</code>
• Arayüz: <code>{len(net_if)} aktif</code>
"""

    reply = await sys_msg.edit_text(response, disable_web_page_preview=True)
    if isinstance(reply, types.Error):
        client.logger.warning(reply.message)