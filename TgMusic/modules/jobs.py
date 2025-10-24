# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

import asyncio
import time
from datetime import datetime, timedelta
from pytdbot import Client, types
from TgMusic.core import chat_cache, call, db, config
from pyrogram import errors
from pyrogram.client import Client as PyroClient


class InactiveCallManager:
    """
    🔄 Otomatik Sesli Sohbet Yönetimi:
      • Uzun süre dinleyici kalmadığında sesli sohbeti otomatik kapatır.
      • Her gün saat 03:00'te tüm yardımcı hesapları (assistant) otomatik olarak gruplardan çıkarır.
    """

    def __init__(self, bot: Client):
        self.bot = bot
        self._stop = asyncio.Event()
        self._vc_task: asyncio.Task | None = None
        self._leave_task: asyncio.Task | None = None
        self._sleep_time = 40  # kontrol aralığı (saniye)

    async def _end_call_if_inactive(self, chat_id: int) -> bool:
        """Dinleyici kalmayan sesli sohbeti sonlandırır."""
        vc_users = await call.vc_users(chat_id)
        if isinstance(vc_users, types.Error):
            self.bot.logger.warning(f"[VC Kullanıcı Hatası] {chat_id}: {vc_users.message}")
            return False

        # En az 2 kişi varsa devam et
        if len(vc_users) > 1:
            return False

        played_time = await call.played_time(chat_id)
        if isinstance(played_time, types.Error):
            self.bot.logger.warning(f"[Oynatma Süresi Hatası] {chat_id}: {played_time.message}")
            return False

        # 15 saniyeden kısa oynatmalar dikkate alınmaz
        if played_time < 15:
            return False

        await self.bot.sendTextMessage(chat_id, "⚠️ Dinleyici bulunamadı. Sesli sohbetten ayrılıyorum...")
        await call.end(chat_id)
        return True

    async def _vc_loop(self):
        """Aktif sesli sohbetleri kontrol eden döngü."""
        while not self._stop.is_set():
            try:
                # Bot henüz başlatılmamışsa bekle
                if self.bot.me is None:
                    await asyncio.sleep(2)
                    continue

                # Otomatik bitirme kapalıysa beklemeye devam et
                if not await db.get_auto_end(self.bot.me.id):
                    await asyncio.sleep(self._sleep_time)
                    continue

                active_chats = chat_cache.get_active_chats()
                if not active_chats:
                    await asyncio.sleep(self._sleep_time)
                    continue

                for chat_id in active_chats:
                    await self._end_call_if_inactive(chat_id)
                    await asyncio.sleep(0.1)

            except Exception as e:
                self.bot.logger.exception(f"[VC Otomatik Bitiş] Döngü hatası: {e}")

            await asyncio.sleep(self._sleep_time)

    async def _leave_loop(self):
        """Her gün 03:00'te tüm yardımcı hesapları gruplardan çıkarır."""
        while not self._stop.is_set():
            try:
                now = datetime.now()
                target = now.replace(hour=3, minute=0, second=0, microsecond=0)
                if now >= target:
                    target += timedelta(days=1)

                wait = (target - now).total_seconds()
                self.bot.logger.info(f"[Oto Çıkış] 03:00’e kadar {wait:.2f} saniye bekleniyor...")
                await asyncio.wait([asyncio.create_task(self._stop.wait())], timeout=wait)

                if self._stop.is_set():
                    break

                await self.leave_all()

                # Güvenlik bekleme (24 saat)
                await asyncio.wait([asyncio.create_task(self._stop.wait())], timeout=86400)
            except Exception as e:
                self.bot.logger.exception(f"[Oto Çıkış] Hata: {e}")
                await asyncio.sleep(3600)  # 1 saat sonra yeniden dene

    async def _leave_chat(self, ub: PyroClient, chat_id: int):
        """Yardımcı hesabı belirtilen gruptan çıkarır."""
        try:
            if chat_cache.is_active(chat_id):
                return False

            await ub.leave_chat(chat_id)
            self.bot.logger.debug(f"[{ub.name}] {chat_id} grubundan çıkıldı.")
            return True

        except errors.FloodWait as e:
            wait_time = e.value
            if wait_time <= 100:
                self.bot.logger.warning(f"[{ub.name}] FloodWait {wait_time}s (chat: {chat_id})")
                await asyncio.sleep(wait_time)
                return await self._leave_chat(ub, chat_id)
            return False

        except errors.RPCError as e:
            self.bot.logger.warning(f"[{ub.name}] RPC Hatası ({chat_id}): {e}")
            return False

        except Exception as e:
            self.bot.logger.exception(f"[{ub.name}] Çıkış hatası ({chat_id}): {e}")
            return False

    async def leave_all(self):
        """Tüm yardımcı hesapları (assistant’ları) gruplardan çıkarır."""
        if not config.AUTO_LEAVE:
            return

        self.bot.logger.info("[Oto Çıkış] leave_all() başlatıldı.")
        start_time = time.monotonic()

        try:
            for client_name, call_instance in call.calls.items():
                ub: PyroClient = call_instance.mtproto_client
                chats_to_leave = []

                try:
                    async for dialog in ub.get_dialogs():
                        chat = getattr(dialog, "chat", None)
                        if chat and chat.id > 0:
                            continue  # özel sohbetleri atla
                        chats_to_leave.append(chat.id)
                except Exception as e:
                    self.bot.logger.exception(f"[{client_name}] Diyaloglar alınamadı: {e}")
                    continue

                self.bot.logger.info(f"[{client_name}] {len(chats_to_leave)} grup bulundu, çıkış yapılıyor...")
                for chat_id in chats_to_leave:
                    await self._leave_chat(ub, chat_id)
                    await asyncio.sleep(0.5)

        except Exception as e:
            self.bot.logger.critical(f"[leave_all] Kritik hata: {e}", exc_info=True)
        finally:
            duration = time.monotonic() - start_time
            self.bot.logger.info(f"[leave_all] Tamamlandı ({duration:.2f} sn)")

    async def start(self):
        """Otomatik döngüleri başlatır."""
        if not self._vc_task or self._vc_task.done():
            self._stop.clear()
            self._vc_task = asyncio.create_task(self._vc_loop())
            self.bot.logger.info("🎧 Sesli sohbet etkinlik kontrolü başlatıldı.")

        if not self._leave_task or self._leave_task.done():
            self._leave_task = asyncio.create_task(self._leave_loop())
            self.bot.logger.info("🕒 Günlük oto-çıkış döngüsü başlatıldı (03:00).")

    async def stop(self):
        """Tüm otomatik işlemleri durdurur."""
        self._stop.set()

        if self._vc_task:
            await self._vc_task

        if self._leave_task:
            await self._leave_task

        self.bot.logger.info("🛑 Tüm arka plan döngüleri durduruldu.")