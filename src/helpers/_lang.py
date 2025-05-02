#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import json
import os

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANG_DIR = "src/locales"
DEFAULT_LANG = "en"

langs = {}

def get_string(key: str, lang: str = DEFAULT_LANG) -> str:
    text = langs.get(lang, {}).get(key)
    if text is not None:
        return text

    # Fallback to default language
    text = langs.get(DEFAULT_LANG, {}).get(key)
    if text is not None:
        logger.warning(
            f"Missing key '{key}' in '{lang}', using fallback from '{DEFAULT_LANG}'."
        )
        return text

    # If missing in default too
    logger.error(
        f"Missing key '{key}' in both '{lang}' and default language '{DEFAULT_LANG}'."
    )
    return key

def load_translations():
    for f_name in os.listdir(LANG_DIR):
        lang_code = f_name.replace(".json", "")
        file_path = os.path.join(LANG_DIR, f_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                langs[lang_code] = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Error decoding JSON for language '{lang_code}' in file '{f_name}': {e}")
        except Exception as e:
            logger.error(f"Error decoding JSON for language '{lang_code}': {e}", exc_info=True)
