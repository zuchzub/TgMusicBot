#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from pytdbot import Client, types

from src import db
from src.helpers import get_string, LangsButtons
from src.modules.utils import Filter
from src.modules.utils.admins import is_owner


@Client.on_message(filters=Filter.command(["lang", "setlang"]))
async def set_language(_: Client, msg: types.Message) -> None:
    await msg.reply_text("Choose your language:", reply_markup=LangsButtons)
    return None


@Client.on_updateNewCallbackQuery(filters=Filter.regex(r"^lang_"))
async def handle_language_cb(_: Client, message: types.UpdateNewCallbackQuery) -> None:
    data = message.payload.data.decode()
    chat_id = message.chat_id
    user_id = message.sender_user_id
    lang_code = data.split("_", 1)[1]

    if chat_id < 0 and not await is_owner(chat_id, user_id):
        await message.answer(get_string("only_owner", lang_code), show_alert=True)
        return None

    await message.answer("Processing...")
    await db.set_lang(chat_id, lang_code)
    await message.edit_message_text(get_string("language_set", lang_code))
    return None
