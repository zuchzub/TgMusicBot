#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import aiofiles
import json
import logging

from pathlib import Path

from pytdbot import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"

LANG_NAMES = {
    "en": "English",
    "hi": "हिन्दी",
    "es": "Spanish",
    "fr": "French",
    "ar": "Arabic",
    "bn": "Bengali",
    "ru": "Russian",
    "id": "Indonesia",
    "kur": "Kurdish",
    "fa": "Persian",
}

langs = {}


async def load_translation(file_path: Path):
    lang_code = file_path.stem
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        langs[lang_code] = json.loads(await f.read())


async def load_translations():
    await asyncio.gather(
        *[load_translation(f) for f in Path("src/locales").glob("*.json")]
    )


def get_string(key: str, lang: str = DEFAULT_LANG) -> str:
    text = langs.get(lang, {}).get(key)
    if text is not None:
        return text

    text = langs.get(DEFAULT_LANG, {}).get(key)
    if text is not None:
        logger.warning(
            f"Missing key '{key}' in '{lang}', using fallback from '{DEFAULT_LANG}'."
        )
        return text
    logger.error(
        f"Missing key '{key}' in both '{lang}' and default language '{DEFAULT_LANG}'."
    )
    return key


def generate_lang_buttons() -> types.ReplyMarkupInlineKeyboard:
    buttons = []
    row = []

    for lang_code, lang_name in sorted(LANG_NAMES.items()):
        row.append(
            types.InlineKeyboardButton(
                text=lang_name,
                type=types.InlineKeyboardButtonTypeCallback(
                    f"lang_{lang_code}".encode()
                ),
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return types.ReplyMarkupInlineKeyboard(buttons)


LangsButtons = generate_lang_buttons()
