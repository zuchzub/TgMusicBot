#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import logging
from logging.handlers import RotatingFileHandler

LOG_FORMAT = (
    "[%(asctime)s - %(levelname)s] - %(name)s - "
    "%(filename)s:%(lineno)d - %(message)s"
)

formatter = logging.Formatter(LOG_FORMAT, datefmt="%d-%b-%y %H:%M:%S")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(
    "bot.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=2,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[stream_handler, file_handler],
)

for lib in ("httpx", "pyrogram", "apscheduler"):
    logging.getLogger(lib).setLevel(logging.WARNING)

# Uncomment below lines for advanced debugging
logging.getLogger("pytgcalls").setLevel(logging.DEBUG)
# logging.getLogger("ffmpeg").setLevel(logging.DEBUG)
logging.getLogger("ntgcalls").setLevel(logging.DEBUG)
# logging.getLogger("webrtc").setLevel(logging.DEBUG)
logging.getLogger("pyrogram").setLevel(logging.DEBUG)

LOGGER = logging.getLogger("TgMusicBot")
