#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
from types import NoneType

from pytdbot import Client, types

from src import call
from src.helpers import db
from src.logger import LOGGER
from src.modules.utils import SupportButton
from src.modules.utils.admins import load_admin_cache
from src.modules.utils.buttons import add_me_button
from src.helpers import chat_cache
from src.modules.utils.play_helpers import user_status_cache


async def handle_non_supergroup(client: Client, chat_id: int) -> None:
    """
    Notify user that the chat is not a supergroup and leave.
    """
    text = (
        f"This chat ({chat_id}) is not a supergroup yet.\n"
        "<b>⚠️ Please convert this chat to a supergroup and add me as admin.</b>\n\n"
        "If you don't know how to convert, use this guide:\n"
        "🔗 https://te.legra.ph/How-to-Convert-a-Group-to-a-Supergroup-01-02\n\n"
        "If you have any questions, join our support group:"
    )
    bot_username = client.me.usernames.editable_username
    await client.sendTextMessage(
        chat_id, text, reply_markup=add_me_button(bot_username)
    )
    await asyncio.sleep(1)
    await client.leaveChat(chat_id)


def is_valid_supergroup(chat_id: int) -> bool:
    """
    Check if a chat ID is for a supergroup.
    """
    return str(chat_id).startswith("-100")


async def handle_bot_join(client: Client, chat_id: int) -> None:
    """
    Handle logic when bot is added to a new chat.
    """
    LOGGER.info("Bot joined the chat %s.", chat_id)
    chat_id = int(str(chat_id)[4:]) if str(chat_id).startswith("-100") else chat_id
    chat_info = await client.getSupergroupFullInfo(chat_id)
    if isinstance(chat_info, types.Error):
        LOGGER.warning("Failed to get supergroup info for %s", chat_id)
        return

    if chat_info.member_count < 50:
        text = (
            f"⚠️ This group has too few members ({chat_info.member_count}).\n\n"
            "To prevent spam and ensure proper functionality, "
            "this bot only works in groups with at least 50 members.\n"
            "Please grow your community and add me again later.\n"
            "If you have any questions, join our support group:"
        )
        await client.sendTextMessage(chat_id, text, reply_markup=SupportButton)
        await asyncio.sleep(1)
        await client.leaveChat(chat_id)
        await db.remove_chat(chat_id)


@Client.on_updateChatMember()
async def chat_member(client: Client, update: types.UpdateChatMember) -> None:
    """
    Handles member updates in the chat (joins, leaves, promotions, demotions, bans, and
    unbans).
    """
    chat_id = update.chat_id
    if chat_id > 0:
        return None

    if not is_valid_supergroup(chat_id):
        return await handle_non_supergroup(client, chat_id)

    try:
        await db.add_chat(chat_id)
        user_id = update.new_chat_member.member_id.user_id
        old_status = update.old_chat_member.status["@type"]
        new_status = update.new_chat_member.status["@type"]

        if user_id == 0:
            return None

        if old_status == "chatMemberStatusLeft" and new_status in {
            "chatMemberStatusMember",
            "chatMemberStatusAdministrator",
        }:
            if user_id == client.options["my_id"]:
                return await handle_bot_join(client, chat_id)

            LOGGER.info("User %s joined the chat %s.", user_id, chat_id)
            return None

        # User left or kicked
        if (
            old_status in {"chatMemberStatusMember", "chatMemberStatusAdministrator"}
            and new_status == "chatMemberStatusLeft"
        ):
            LOGGER.info("User %s left or was kicked from %s.", user_id, chat_id)
            ub = await call.get_client(chat_id)
            if isinstance(ub, (types.Error, NoneType)):
                return None
            user_key = f"{chat_id}:{ub.me.id}"
            if user_id == ub.me.id:
                user_status_cache[user_key] = "chatMemberStatusLeft"
            return None

        # User banned
        if new_status == "chatMemberStatusBanned":
            LOGGER.info("User %s was banned in %s.", user_id, chat_id)
            ub = await call.get_client(chat_id)
            if isinstance(ub, (types.Error, NoneType)):
                return None

            user_key = f"{chat_id}:{ub.me.id}"
            if user_id == ub.me.id:
                user_status_cache[user_key] = "chatMemberStatusBanned"
            return None

        # User unbanned
        if (
            old_status == "chatMemberStatusBanned"
            and new_status == "chatMemberStatusLeft"
        ):
            LOGGER.info("User %s was unbanned in %s.", user_id, chat_id)
            ub = await call.get_client(chat_id)
            if isinstance(ub, (types.Error, NoneType)):
                return None
            user_key = f"{chat_id}:{ub.me.id}"
            if user_id == ub.me.id:
                user_status_cache[user_key] = "chatMemberStatusLeft"
            return None

        # Promotions/Demotions
        is_promoted = (
            old_status != "chatMemberStatusAdministrator"
            and new_status == "chatMemberStatusAdministrator"
        )
        is_demoted = (
            old_status == "chatMemberStatusAdministrator"
            and new_status != "chatMemberStatusAdministrator"
        )

        if user_id == client.options["my_id"] and is_promoted:
            LOGGER.info("Bot promoted in %s. Reloading admin cache.", chat_id)
            await load_admin_cache(client, chat_id, True)
            return None

        if is_promoted or is_demoted:
            action = "promoted" if is_promoted else "demoted"
            LOGGER.info("User %s was %s in %s.", user_id, action, chat_id)
            await load_admin_cache(client, chat_id, True)
            return None
        return None

    except Exception as e:
        LOGGER.error("Error processing chat member update in %s: %s", chat_id, e)
        return None


@Client.on_updateNewMessage(position=1)
async def new_message(client: Client, update: types.UpdateNewMessage) -> None:
    """
    Handle new messages for video chat events.
    """
    message = update.message
    if not message:
        return None
    chat_id = message.chat_id
    content = message.content
    if isinstance(content, types.MessageVideoChatEnded):
        LOGGER.info("Video chat ended in %s", chat_id)
        chat_cache.clear_chat(chat_id)
        await client.sendTextMessage(chat_id, "Video chat ended!\nall queues cleared")
        return None
    if isinstance(content, types.MessageVideoChatStarted):
        LOGGER.info("Video chat started in %s", chat_id)
        chat_cache.clear_chat(chat_id)
        await client.sendTextMessage(
            chat_id, "Video chat started!\nuse /play song name to play a song"
        )
        return None
    LOGGER.debug("New message in %s: %s", chat_id, message)
    return None
