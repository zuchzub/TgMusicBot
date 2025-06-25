#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from typing import Union

from pytdbot import filters, types


class Filter:
    @staticmethod
    def _extract_text(event) -> str | None:
        """
        Extract text from an event. If the event is a message, it will get the text from
        the message. If the event is an update, it will get the text from the message.
        If the event is a callback query, it will decode the data using UTF-8 and return
        the result. If it can't extract the text, it will return None.

        :param event: The event to extract the text from.
        :return: The text extracted from the event, or None if the text couldn't be
            extracted.
        """
        if isinstance(event, types.Message) and isinstance(
            event.content, types.MessageText
        ):
            return event.content.text.text
        if isinstance(event, types.UpdateNewMessage) and isinstance(
            event.message, types.MessageText
        ):
            return event.message.text.text
        if isinstance(event, types.UpdateNewCallbackQuery) and event.payload:
            return event.payload.data.decode()

        return None

    @staticmethod
    def command(
        commands: Union[str, list[str]], prefixes: str = "/!"
    ) -> filters.Filter:
        """
        Filter for commands.

        Supports multiple commands and prefixes like / or !. Also handles commands with
        @mentions (e.g., /start@BotName).
        """
        if isinstance(commands, str):
            commands = [commands]
        commands_set = {cmd.lower() for cmd in commands}

        pattern = re.compile(
            rf"^[{re.escape(prefixes)}](\w+)(?:@(\w+))?", re.IGNORECASE
        )

        async def filter_func(client, event) -> bool:
            text = Filter._extract_text(event)
            if not text:
                return False

            match = pattern.match(text.strip())
            if not match:
                return False

            cmd, mentioned_bot = match.groups()
            if cmd.lower() not in commands_set:
                return False

            if mentioned_bot:
                bot_username = client.me.usernames.editable_username
                return bot_username and mentioned_bot.lower() == bot_username.lower()

            return True

        return filters.create(filter_func)

    @staticmethod
    def regex(pattern: str) -> filters.Filter:
        """
        Filter for messages or callback queries matching a regex pattern.
        """

        compiled = re.compile(pattern)

        async def filter_func(_, event) -> bool:
            text = Filter._extract_text(event)
            return bool(compiled.search(text)) if text else False

        return filters.create(filter_func)

    @staticmethod
    def user(user_ids: Union[int, list[int]]) -> filters.Filter:
        """
        Filter for specific user IDs.
        """
        user_ids = {user_ids} if isinstance(user_ids, int) else set(user_ids)

        async def filter_func(_, event) -> bool:
            sender = event.sender_id

            if isinstance(sender, types.MessageSenderChat):
                return sender.chat_id in user_ids
            elif isinstance(sender, types.MessageSenderUser):
                return sender.user_id in user_ids

            return False

        return filters.create(filter_func)

    @staticmethod
    def chat(chat_ids: Union[int, list[int]]) -> filters.Filter:
        """
        Filter for specific chat IDs.
        """
        chat_ids = {chat_ids} if isinstance(chat_ids, int) else set(chat_ids)

        async def filter_func(_, event) -> bool:
            return getattr(event, "chat_id", None) in chat_ids

        return filters.create(filter_func)
