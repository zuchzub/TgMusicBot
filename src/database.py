#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from typing import Optional

from cachetools import TTLCache
from motor.motor_asyncio import AsyncIOMotorClient

import config
from src.logger import LOGGER


class Database:
    def __init__(self):
        """
        Initialize a new Database object.

        This creates a new connection to a MongoDB server using the URI
        specified in the `config.MONGO_URI` variable. The connection is
        stored in the `mongo_client` attribute.

        The `chat_db`, `users_db`, and `bot_db` attributes are set to the
        "chats", "users", and "bot" collections in the "MusicBot" database,
        respectively. The `chat_cache` and `bot_cache` attributes are set to
        `TTLCache` objects with a maximum size of 1000 and a time to live of
        600 seconds.
        """
        self.mongo_client = AsyncIOMotorClient(config.MONGO_URI)
        _db = self.mongo_client["MusicBot"]
        self.chat_db = _db["chats"]
        self.users_db = _db["users"]
        self.bot_db = _db["bot"]

        self.chat_cache = TTLCache(maxsize=1000, ttl=600)
        self.bot_cache = TTLCache(maxsize=1000, ttl=600)

    async def ping(self) -> None:
        """
        Tests the connection to the MongoDB server.

        This is a simple test of whether the database connection is working. It sends a
        "ping" command to the MongoDB server and logs a message if the connection is
        successful, or raises an exception if the connection fails.

        This function does not return any value, but will log a message to the logger if
        the connection is successful, or raise an exception if the connection fails.
        """
        try:
            await self.mongo_client.admin.command("ping")
            LOGGER.info("Database connection completed.")
        except Exception as e:
            LOGGER.error("Database connection failed: %s", e)
            raise

    async def get_chat(self, chat_id: int) -> Optional[dict]:
        """
        Get the document for a given chat ID from the database.

        This will first check the cache to see if we've already retrieved the
        chat document for the given `chat_id`. If we have, it will return the
        cached document. If not, it will query the database and cache the
        result.

        If any error occurs during the database query, it will log the error
        and return `None`.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to retrieve the document for.

        Returns
        -------
        Optional[dict]
            The document for the given chat ID, or `None` if an error occurred.
        """
        if chat_id in self.chat_cache:
            return self.chat_cache[chat_id]
        try:
            if chat := await self.chat_db.find_one({"_id": chat_id}):
                self.chat_cache[chat_id] = chat
            return chat
        except Exception as e:
            LOGGER.warning("Error getting chat: %s", e)
            return None

    async def add_chat(self, chat_id: int) -> None:
        """
        Add a chat to the database.

        This function will check if the chat ID already exists in the database. If
        it does not, it will add the chat to the database.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to add to the database.

        Returns
        -------
        None
        """
        if await self.get_chat(chat_id) is None:
            LOGGER.info("Added chat: %s", chat_id)
            await self.chat_db.insert_one({"_id": chat_id})

    async def _update_chat_field(self, chat_id: int, key: str, value) -> None:
        """
        Update a specific field in the chat document and cache.

        This function updates a field specified by `key` with the provided `value`
        in the chat document corresponding to `chat_id` in the database. If the
        chat document does not exist, it will be created. The function also
        updates the cached chat data with the new value.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to update.
        key : str
            The field name to update in the chat document.
        value : any
            The new value to set for the specified field.

        Returns
        -------
        None
        """
        await self.chat_db.update_one(
            {"_id": chat_id}, {"$set": {key: value}}, upsert=True
        )
        cached = self.chat_cache.get(chat_id, {})
        cached[key] = value
        self.chat_cache[chat_id] = cached

    async def get_play_type(self, chat_id: int) -> int:
        """
        Get the play type for a given chat.

        The play type is a preference for a given chat that determines how the
        bot should handle song requests. If the preference is 0, the bot will
        immediately play the first search result. If the preference is 1, the
        bot will send a list of songs to choose from.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to get the play type for.

        Returns
        -------
        int
            The play type for the given chat, or 0 if the chat does not exist in
            the database.
        """
        chat = await self.get_chat(chat_id)
        return chat.get("play_type", 0) if chat else 0

    async def set_play_type(self, chat_id: int, play_type: int) -> None:
        """
        Set the play type for a given chat.

        This function updates the play type preference for the specified chat ID
        in the database and cache. The play type determines how the bot should
        handle song requests: a value of 0 means immediately playing the first
        search result, while a value of 1 means providing a list of songs to
        choose from.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to update the play type for.
        play_type : int
            The play type preference to set for the chat (0 or 1).

        Returns
        -------
        None
        """
        await self._update_chat_field(chat_id, "play_type", play_type)

    async def get_assistant(self, chat_id: int) -> Optional[str]:
        """
        Get the assistant associated with a given chat ID.

        If a chat ID has an associated assistant, it means that the assistant
        is responsible for handling song requests for the chat. This function
        will return the ID of the Pyrogram client for the assistant associated
        with the given chat ID, or `None` if no assistant is associated or if
        the chat ID does not exist in the database.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to get the assistant for.

        Returns
        -------
        Optional[str]
            The ID of the Pyrogram client for the assistant associated with the
            given chat ID, or `None` if no assistant is associated or if the
            chat does not exist in the database.
        """
        chat = await self.get_chat(chat_id)
        return chat.get("assistant") if chat else None

    async def set_assistant(self, chat_id: int, assistant: str) -> None:
        """
        Set the assistant associated with a given chat ID.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to set the assistant for.
        assistant : str
            The ID of the Pyrogram client for the assistant to associate with
            the given chat ID.

        Returns
        -------
        None
        """
        await self._update_chat_field(chat_id, "assistant", assistant)

    async def remove_assistant(self, chat_id: int) -> None:
        """
        Remove the assistant associated with a given chat ID.

        This function sets the 'assistant' field to `None` in the chat document
        for the specified chat ID, effectively disassociating any assistant from
        the chat. It updates both the database and the cache.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to remove the assistant from.

        Returns
        -------
        None
        """
        await self._update_chat_field(chat_id, "assistant", None)

    async def add_auth_user(self, chat_id: int, auth_user: int) -> None:
        """
        Add a user to the list of authorized users for a given chat.

        This function adds the user with the ID `auth_user` to the list of
        authorized users for the chat with the ID `chat_id`. If the chat
        document does not exist, it will be created. The function also updates
        the cached chat data with the new value.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to add the authorized user to.
        auth_user : int
            The ID of the user to add to the list of authorized users for the
            given chat.

        Returns
        -------
        None
        """
        await self.chat_db.update_one(
            {"_id": chat_id}, {"$addToSet": {"auth_users": auth_user}}, upsert=True
        )
        chat = await self.get_chat(chat_id)
        auth_users = chat.get("auth_users", [])
        if auth_user not in auth_users:
            auth_users.append(auth_user)
        self.chat_cache[chat_id]["auth_users"] = auth_users

    async def remove_auth_user(self, chat_id: int, auth_user: int) -> None:
        """
        Remove a user from the list of authorized users for a given chat.

        This function removes the user with the ID `auth_user` from the list of
        authorized users for the chat with the ID `chat_id`. It updates the
        database and the cached chat data to reflect the removal.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to remove the authorized user from.
        auth_user : int
            The ID of the user to remove from the list of authorized users for
            the given chat.

        Returns
        -------
        None
        """
        await self.chat_db.update_one(
            {"_id": chat_id}, {"$pull": {"auth_users": auth_user}}
        )
        chat = await self.get_chat(chat_id)
        auth_users = chat.get("auth_users", [])
        if auth_user in auth_users:
            auth_users.remove(auth_user)
        self.chat_cache[chat_id]["auth_users"] = auth_users

    async def reset_auth_users(self, chat_id: int) -> None:
        """
        Reset the list of authorized users for a given chat.

        This function resets the list of authorized users for the chat with the
        ID `chat_id` to an empty list. It updates the database and the cached
        chat data to reflect the reset.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to reset the authorized users for.

        Returns
        -------
        None
        """
        await self._update_chat_field(chat_id, "auth_users", [])

    async def get_auth_users(self, chat_id: int) -> list[int]:
        """
        Retrieve the list of authorized users for a given chat.

        This function fetches the list of user IDs that have been granted
        authorization in the chat identified by `chat_id`. If the chat does
        not exist or no users have been authorized, an empty list is returned.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to retrieve the authorized users for.

        Returns
        -------
        list[int]
            A list of user IDs who are authorized in the specified chat.
        """
        chat = await self.get_chat(chat_id)
        return chat.get("auth_users", []) if chat else []

    async def is_auth_user(self, chat_id: int, user_id: int) -> bool:
        """
        Check if a user is authorized in a given chat.

        This function checks whether the user with the specified `user_id`
        is in the list of authorized users for the chat identified by `chat_id`.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to check authorization for.
        user_id : int
            The ID of the user to check authorization status for.

        Returns
        -------
        bool
            True if the user is authorized in the specified chat, False otherwise.
        """
        return user_id in await self.get_auth_users(chat_id)

    async def set_buttons_status(self, chat_id: int, status: bool) -> None:
        """
        Set the status of buttons for a given chat.

        This function updates the button status for the specified chat ID
        in the database and cache. The button status determines whether
        buttons are enabled or disabled for the chat.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to set the button status for.
        status : bool
            The button status to set for the chat (True for enabled, False for disabled).

        Returns
        -------
        None
        """
        await self._update_chat_field(chat_id, "buttons", status)

    async def get_buttons_status(self, chat_id: int) -> bool:
        """
        Get the status of buttons for a given chat.

        This function retrieves the button status for the specified chat ID
        from the database and cache. The button status determines whether
        buttons are enabled or disabled for the chat.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to get the button status for.

        Returns
        -------
        bool
            True if the button status is enabled for the specified chat, False otherwise.
        """
        chat = await self.get_chat(chat_id)
        return chat.get("buttons", True) if chat else True

    async def set_thumb_status(self, chat_id: int, status: bool) -> None:
        """
        Set the status of thumbnails for a given chat.

        This function updates the thumbnail status for the specified chat ID
        in the database and cache. The thumbnail status determines whether
        thumbnails are displayed in the chat or not.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to set the thumbnail status for.
        status : bool
            The thumbnail status to set for the chat (True for enabled, False for disabled).

        Returns
        -------
        None
        """
        await self._update_chat_field(chat_id, "thumb", status)

    async def get_thumb_status(self, chat_id: int) -> bool:
        """
        Retrieve the thumbnail status for a given chat.

        This function retrieves the thumbnail status for the specified chat ID
        from the database and cache. The thumbnail status determines whether
        thumbnails are displayed in the chat.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to get the thumbnail status for.

        Returns
        -------
        bool
            True if the thumbnail status is enabled for the specified chat,
            False otherwise.
        """
        chat = await self.get_chat(chat_id)
        return chat.get("thumb", True) if chat else True

    async def remove_chat(self, chat_id: int) -> None:
        """
        Remove a chat from the database.

        This function removes the chat document for the specified chat ID
        from the database and cache.

        Parameters
        ----------
        chat_id : int
            The ID of the chat to remove from the database.

        Returns
        -------
        None
        """
        await self.chat_db.delete_one({"_id": chat_id})
        self.chat_cache.pop(chat_id, None)

    async def add_user(self, user_id: int) -> None:
        """
        Add a user to the database.

        This function adds a user with the specified `user_id` to the database.
        If the user already exists, it will not be added again.

        Parameters
        ----------
        user_id : int
            The ID of the user to add to the database.

        Returns
        -------
        None
        """
        if await self.is_user_exist(user_id):
            return
        LOGGER.info("Added user: %s", user_id)
        await self.users_db.insert_one({"_id": user_id})

    async def remove_user(self, user_id: int) -> None:
        """
        Remove a user from the database.

        This function removes the user document for the specified `user_id` from
        the database.

        Parameters
        ----------
        user_id : int
            The ID of the user to remove from the database.

        Returns
        -------
        None
        """
        await self.users_db.delete_one({"_id": user_id})

    async def is_user_exist(self, user_id: int) -> bool:
        """
        Check if a user exists in the database.

        This function checks whether a user with the specified `user_id` exists
        in the database. It returns `True` if the user exists, and `False`
        otherwise.

        Parameters
        ----------
        user_id : int
            The ID of the user to check for existence in the database.

        Returns
        -------
        bool
            True if the user exists in the database, False otherwise.
        """
        return await self.users_db.find_one({"_id": user_id}) is not None

    async def get_all_users(self) -> list[int]:
        """
        Retrieve all user IDs from the database.

        This function queries the database to retrieve a list of all user
        IDs stored in the "users" collection. It returns the list of user
        IDs as integers.

        Returns
        -------
        list[int]
            A list of user IDs present in the database.
        """
        return [user["_id"] async for user in self.users_db.find()]

    async def get_all_chats(self) -> list[int]:
        """
        Retrieve all chat IDs from the database.

        This function queries the database to retrieve a list of all chat
        IDs stored in the "chats" collection. It returns the list of chat
        IDs as integers.

        Returns
        -------
        list[int]
            A list of chat IDs present in the database.
        """
        return [chat["_id"] async for chat in self.chat_db.find()]

    async def get_logger_status(self, bot_id: int) -> bool:
        """
        Retrieve the logger status for a given bot ID.

        This function retrieves the logger status for the bot with the
        specified `bot_id` from the database. If the bot does not exist,
        it will return `False`. If the bot exists and has a logger status
        set, it will return the logger status. If the bot exists but does
        not have a logger status set, it will return `False`.

        Parameters
        ----------
        bot_id : int
            The ID of the bot to retrieve the logger status for.

        Returns
        -------
        bool
            The logger status for the specified bot.
        """
        if bot_id in self.bot_cache:
            return self.bot_cache[bot_id]

        bot_data = await self.bot_db.find_one({"_id": bot_id})
        status = bot_data.get("logger", False) if bot_data else False
        self.bot_cache[bot_id] = status
        return status

    async def set_logger_status(self, bot_id: int, status: bool) -> None:
        """
        Set the logger status for a given bot ID.

        This function sets the logger status for the bot with the specified
        `bot_id` to the specified `status` in the database. If the bot does
        not exist, it will be created. If the bot exists and has a logger
        status set, it will be updated.

        Parameters
        ----------
        bot_id : int
            The ID of the bot to set the logger status for.
        status : bool
            The logger status to set for the bot.

        Returns
        -------
        None
        """
        await self.bot_db.update_one(
            {"_id": bot_id}, {"$set": {"logger": status}}, upsert=True
        )
        self.bot_cache[bot_id] = status

    async def close(self) -> None:
        """
        Close the database connection.

        This function closes the connection to the MongoDB database. It
        should be called when the bot is shutting down.

        Returns
        -------
        None
        """
        self.mongo_client.close()
        LOGGER.info("Database connection closed.")


db: Database = Database()
