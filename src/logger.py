#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ],
)

# Reduce logging verbosity for third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# logging.getLogger('pytgcalls').setLevel(logging.DEBUG)
# logging.getLogger('ffmpeg').setLevel(logging.DEBUG)
# logging.getLogger('ntgcalls').setLevel(logging.DEBUG)
# logging.getLogger('webrtc').setLevel(logging.DEBUG)

LOGGER = logging.getLogger("Bot")
