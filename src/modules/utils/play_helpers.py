#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from types import NoneType
from typing import Any, Literal, Optional, Union

import pyrogram
from cachetools import TTLCache
from pyrogram import errors
from pytdbot import Client, types

from src.logger import LOGGER

user_status_cache = TTLCache(maxsize=5000, ttl=1000)
chat_invite_cache = TTLCache(maxsize=1000, ttl=1000)


async def get_url(
    msg: types.Message, reply: Union[types.Message, None]
) -> Optional[str]:
    """
    Extracts a URL from the given message or its reply.

    Args:
    msg: The message object to extract the URL from.
    reply: The reply message objects to extract the URL from, if any.

    Returns:
    The extracted URL string, or `None` if no URL was found.
    """
    if reply:
        text_content = reply.text or ""
        entities = reply.entities or []
    else:
        text_content = msg.text or ""
        entities = msg.entities or []

    for entity in entities:
        if entity.type and entity.type["@type"] == "textEntityTypeUrl":
            offset = entity.offset
            length = entity.length
            url = text_content[offset : offset + length]
            LOGGER.info("Extracted URL: %s", url)
            return url
    return None


def extract_argument(text: str, enforce_digit: bool = False) -> str | None:
    """
    Extracts the argument from the command text.

    Args:
        text (str): The full command text.
        enforce_digit (bool): Whether to enforce that the argument is a digit.

    Returns:
        str | None: The extracted argument or None if invalid.
    """
    args = text.strip().split(maxsplit=1)

    if len(args) < 2:
        return None

    argument = args[1].strip()
    return None if enforce_digit and not argument.isdigit() else argument


async def del_msg(msg: types.Message):
    """
    Deletes the given message.

    Args:
        msg (types.Message): The message to delete.

    Returns:
        None
    """
    delete = await msg.delete()
    if isinstance(delete, types.Error):
        if delete.code == 400:
            return
        LOGGER.warning("Error deleting message: %s", delete)


async def edit_text(
    reply_message: types.Message, *args: Any, **kwargs: Any
) -> Union["types.Error", "types.Message"]:
    """
    Edits the given message and returns the result.

    If the given message is an Error, logs the error and returns it.
    If an exception occurs while editing the message, logs the exception and
    returns the original message.

    Args:
        reply_message (types.Message): The message to edit.
        *args: Passed to `Message.edit_text`.
        **kwargs: Passed to `Message.edit_text`.

    Returns:
        Union["types.Error", "types.Message"]: The edited message, or the
        original message if an exception occurred.
    """
    if isinstance(reply_message, types.Error):
        LOGGER.warning("Error getting message: %s", reply_message)
        return reply_message
    try:
        return await reply_message.edit_text(*args, **kwargs)
    except Exception as e:
        LOGGER.warning("Error editing message: %s", e)
        return reply_message


async def join_ub(chat_id: int, c: Client, ub: pyrogram.Client):
    """
    Handles the userbot joining a chat via invite link or approval.
    """
    invite_link = chat_invite_cache.get(chat_id, await c.createChatInviteLink(chat_id))
    if isinstance(invite_link, types.Error):
        return invite_link

    if isinstance(invite_link, types.ChatInviteLink):
        invite_link = invite_link.invite_link

    if not invite_link:
        return types.Error(
            code=400, message=f"Failed to get invite link for chat {chat_id}"
        )

    chat_invite_cache[chat_id] = invite_link
    invite_link = invite_link.replace("https://t.me/+", "https://t.me/joinchat/")
    if isinstance(ub.me, (NoneType, types.Error)):
        return types.Error(code=400, message="Failed to get userbot info")

    user_key = f"{chat_id}:{ub.me.id}"
    try:
        await ub.join_chat(invite_link)
        user_status_cache[user_key] = "chatMemberStatusMember"
        return None
    except errors.InviteHashExpired:
        return types.Error(
            message=(
                f"It seems my assistant ({ub.me.id}) is either banned from chat {chat_id}, "
                "or doesn't have permission to unban members.\n\n"
                "Please use /reload to verify the current status."
            )
        )
    except errors.InviteRequestSent:
        ok = await c.processChatJoinRequest(
            chat_id=chat_id, user_id=ub.me.id, approve=True
        )
        return ok if isinstance(ok, types.Error) else None
    except errors.UserAlreadyParticipant:
        user_status_cache[user_key] = "chatMemberStatusMember"
        return None
    except Exception as e:
        return types.Error(code=400, message=f"Failed to join chat {chat_id}: {e}")


async def unban_ub(c: Client, chat_id: int, user_id: int):
    """
    Unbans a user from a chat.
    """
    await c.setChatMemberStatus(
        chat_id=chat_id,
        member_id=types.MessageSenderUser(user_id),
        status=types.ChatMemberStatusMember(),
    )


async def check_user_status(c: Client, chat_id: int, user_id: int) -> (
    Literal[
        "chatMemberStatusLeft",
        "chatMemberStatusCreator",
        "chatMemberStatusAdministrator",
        "chatMemberStatusMember",
        "chatMemberStatusRestricted",
        "chatMemberStatusBanned",
    ]
    | Any
):
    """
    Checks the status of a user in a chat.
    """
    user_status = user_status_cache.get((chat_id, user_id))
    if not user_status:
        user = await c.getChatMember(
            chat_id=chat_id, member_id=types.MessageSenderUser(user_id)
        )
        if isinstance(user, types.Error) or user.status is None:
            if user.code == 400:
                return types.ChatMemberStatusLeft().getType()
            else:
                raise user
        user_status = user.status.getType()
        user_status_cache[(chat_id, user_id)] = user_status
    return user_status
