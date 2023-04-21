import re
import logging
from collections import namedtuple
from telegram.ext import CallbackContext
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

class AdminMenuManager:
    """
    A class for handling the admin menu and related callback methods for GPTBot.
    """

    # Define named tuples to group constant values
    Constants = namedtuple("Constants", [
        "SET_NEW_LIMIT",
        "REMOVE_LIMIT",
        "SHOW_LIMIT",
        "SHOW_REMAINING_MESSAGES",
        "IS_TO_SET_NEW_LIMIT",
        "TOGGLE_NOTIFICATIONS",
        "ADD_CHAT_ID",
        "GET_CHAT_ID"
        ])
    FinancialConstants = namedtuple('FinancialConstants', [
        'SET_NEW_DOLLAR_LIMIT',
        'REMOVE_DOLLAR_LIMIT',
        'SHOW_DOLLAR_LIMIT',
        'SHOW_REMAINING_DOLLARS',
        "IS_TO_SET_NEW_USD_LIMIT"
    ])

    def __init__(self, message_limit_handler, financial_validator):
        self.message_limit_handler = message_limit_handler
        self.financial_validator = financial_validator
        
        self.admin_notification_chat_map = {}
        self.silenced_notifications = {} # To track if admins notifications are active
        
        # Initialize constants
        self.constants = self.Constants(
            SET_NEW_LIMIT="set_new_limit",
            REMOVE_LIMIT="remove_limit",
            SHOW_LIMIT="show_limit",
            SHOW_REMAINING_MESSAGES="show_remaining_messages",
            IS_TO_SET_NEW_LIMIT="is_to_set_new_limit",
            TOGGLE_NOTIFICATIONS="toggle_notifications",
            ADD_CHAT_ID="add_chat_id",
            GET_CHAT_ID="get_chat_id"
        )

        self.fin_constants = self.FinancialConstants(
            SET_NEW_DOLLAR_LIMIT="set_new_dollar_limit",
            REMOVE_DOLLAR_LIMIT="remove_dollar_limit",
            SHOW_DOLLAR_LIMIT="show_dollar_limit",
            SHOW_REMAINING_DOLLARS="show_remaining_dollars",
            IS_TO_SET_NEW_USD_LIMIT="is_to_set_new_usd_limit"
        )
        
    def is_user_admin(self, user_id: int, chat_id: int, context: CallbackContext) -> bool:
        chat_member = context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return chat_member.status in ['administrator', 'creator']
        
    def show_admin_menu(self, update: Update, context: CallbackContext):
        user_id = update.message.from_user.id if isinstance(update, Update) else update.from_user.id
        chat_id = update.message.chat.id if isinstance(update, Update) else update.message.chat.id
        message_method = update.message if isinstance(update, Update) else update.message

        if self.is_user_admin(user_id, chat_id, context):
            keyboard = [
            [InlineKeyboardButton("Set Messages Limit", callback_data=self.constants.SET_NEW_LIMIT),
            InlineKeyboardButton("Set $ limit", callback_data=self.fin_constants.SET_NEW_DOLLAR_LIMIT)],
            [InlineKeyboardButton("Show Messages Limit", callback_data=self.constants.SHOW_LIMIT),
            InlineKeyboardButton("Show $ limit", callback_data=self.fin_constants.SHOW_DOLLAR_LIMIT)],
            [InlineKeyboardButton("Remove Messages Limit", callback_data=self.constants.REMOVE_LIMIT),
            InlineKeyboardButton("Remove $ limit", callback_data=self.fin_constants.REMOVE_DOLLAR_LIMIT)],
            [InlineKeyboardButton("Messages Left", callback_data=self.constants.SHOW_REMAINING_MESSAGES),
            InlineKeyboardButton("$ Left", callback_data=self.fin_constants.SHOW_REMAINING_DOLLARS)],
            [InlineKeyboardButton("Add chat ID", callback_data=self.constants.ADD_CHAT_ID)],
            [InlineKeyboardButton("Get current chat ID", callback_data=self.constants.GET_CHAT_ID)]
            ]

            silence_button_text = "Mute notifications" if self.admin_notifications_enabled(chat_id) else "Unmute notifications"
            keyboard.append([InlineKeyboardButton(silence_button_text, callback_data=self.constants.TOGGLE_NOTIFICATIONS)])

            reply_markup = InlineKeyboardMarkup(keyboard)
            message_method.reply_text('Admin Menu:', reply_markup=reply_markup)
        else:
            message_method.reply_text("Sorry, this menu is only available for admins.")
        
    def handle_admin_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        user = query.from_user
        chat = query.message.chat
        data = query.data

        if self.is_user_admin(user.id, chat.id, context):
            if data == self.constants.SET_NEW_LIMIT:
                self.set_new_limit_callback(query, context)
            elif data == self.constants.REMOVE_LIMIT:
                self.remove_limit_callback(query, context)
            elif data == self.constants.SHOW_LIMIT:
                self.show_limit_callback(query, context)
            elif data == self.constants.SHOW_REMAINING_MESSAGES:
                self.show_remaining_messages_callback(query, context)
            elif data == self.fin_constants.SET_NEW_DOLLAR_LIMIT:
                self.set_new_usd_limit_callback(query, context)
            elif data == self.fin_constants.REMOVE_DOLLAR_LIMIT:
                self.remove_usd_limit_callback(query, context)
            elif data == self.fin_constants.SHOW_DOLLAR_LIMIT:
                self.show_usd_limit_callback(query, context)
            elif data == self.fin_constants.SHOW_REMAINING_DOLLARS:
                self.show_remaining_usd_callback(query, context)
            elif data == self.constants.TOGGLE_NOTIFICATIONS:
                self.toggle_admin_notifications(chat.id)
                self.show_admin_menu(query, context)
            elif data == self.constants.ADD_CHAT_ID:
                self.handle_add_chat_id(query, context)
            elif query.data == self.constants.GET_CHAT_ID:
                self.get_current_chat_id_callback(query, context)
        else:
            query.answer("You must be an admin to use these functions.")

    def get_current_chat_id_callback(self, query, context: CallbackContext):
        chat_id = query.message.chat_id
        message = f"Current chat ID: {chat_id}"
        logging.info(message)
        query.answer(message)

    def handle_add_chat_id(self, query, context: CallbackContext):
        user_id = query.from_user.id
        chat_id = query.message.chat_id

        context.user_data[self.constants.ADD_CHAT_ID] = chat_id
        context.bot.send_message(
            chat_id=query.from_user.id,
            text="Please enter chat id of the group from which you would like to receive notifications in this group."
            )

    def set_new_limit_callback(self, query, context: CallbackContext):
        user_id = query.from_user.id
        chat_id = query.message.chat_id

        context.user_data[self.constants.IS_TO_SET_NEW_LIMIT] = chat_id
        context.bot.send_message(chat_id=query.from_user.id, text="Please enter the new message limit value as an integer.")

    def remove_limit_callback(self, query, context: CallbackContext):
        chat_id = query.message.chat.id

        if self.message_limit_handler.has_limit(chat_id):
            self.message_limit_handler.remove_limit(chat_id)
            context.bot.send_message(chat_id=query.from_user.id, text="The bot's message limit for your chat has been removed.")
        else:
            context.bot.send_message(chat_id=query.from_user.id, text="There is no message limit set for your chat.")

    def show_limit_callback(self, query, context: CallbackContext):
        chat_id = query.message.chat.id

        if self.message_limit_handler.has_limit(chat_id):
            limit = self.message_limit_handler.get_limit(chat_id)
            context.bot.send_message(chat_id=query.from_user.id, text=f"The bot's daily limit for your chat is set to {limit} messages.")
        else:
            context.bot.send_message(chat_id=query.from_user.id, text="There is no message limit set for your chat.")

    def show_remaining_messages_callback(self, query, context: CallbackContext):
        chat_id = query.message.chat.id
        
        if not self.message_limit_handler.has_limit(chat_id):
            context.bot.send_message(chat_id=query.from_user.id, text="There is no limit on the remaining messages.")
        else:
            remaining_messages = self.message_limit_handler.get_remaining_messages(chat_id)
            context.bot.send_message(chat_id=query.from_user.id, text=f"There are {remaining_messages} messages left before the daily limit is reached.")

    def set_new_usd_limit_callback(self, query, context: CallbackContext):
        user_id = query.from_user.id
        chat_id = query.message.chat_id

        if self.is_user_admin(user_id, chat_id, context):
            context.user_data[self.fin_constants.IS_TO_SET_NEW_USD_LIMIT] = chat_id
            context.bot.send_message(chat_id=query.from_user.id, text="Please enter the new USD limit value as an integer.")
        else:
            context.bot.send_message(chat_id=query.from_user.id, text="You must be an admin to change the bot's USD limit.")
    
    def remove_usd_limit_callback(self, query, context: CallbackContext):
        chat_id = query.message.chat_id
        self.financial_validator.remove_limit(chat_id)
        context.bot.send_message(chat_id=query.from_user.id, text="The bot's daily USD limit for your chat has been removed.")
    
    def show_usd_limit_callback(self, query, context: CallbackContext):
        chat_id = query.message.chat_id
        limit = self.financial_validator.get_limit(chat_id)
        if limit is not None:
            context.bot.send_message(chat_id=query.from_user.id, text=f"The bot's daily limit for your chat is {limit} USD.")
        else:
            context.bot.send_message(chat_id=query.from_user.id, text="There is no daily USD limit set for your chat.")
    
    def show_remaining_usd_callback(self, query, context: CallbackContext):
        chat_id = query.message.chat_id
        remaining_dollars = self.financial_validator.left_dollar_usage(chat_id)
    
        if remaining_dollars == float("inf"):
            message = "There is no USD limit for your chat."
        else:
            message = f"The remaining spending limit for your chat is {int(remaining_dollars)} USD."

        context.bot.send_message(chat_id=query.from_user.id, text=message)
        
    def handle_text(self, update: Update, context: CallbackContext):
        user_data = context.user_data
        new_limit_str = update.message.text

        is_to_set_new_limit = user_data.get(self.constants.IS_TO_SET_NEW_LIMIT)
        is_to_set_new_usd_limit = user_data.get(self.fin_constants.IS_TO_SET_NEW_USD_LIMIT)
        is_add_chat_id = user_data.get(self.constants.ADD_CHAT_ID)

        if is_to_set_new_limit or is_to_set_new_usd_limit:
            if new_limit_str.isdigit():
                new_limit = int(new_limit_str)
                if is_to_set_new_limit:
                    self.set_new_limit(update, user_data, new_limit, is_usd=False)
                elif is_to_set_new_usd_limit:
                    self.set_new_limit(update, user_data, new_limit, is_usd=True)
            else:
                update.message.reply_text("Please provide a valid integer value for the new limit.")
            user_data[self.constants.IS_TO_SET_NEW_LIMIT] = None
            user_data[self.fin_constants.IS_TO_SET_NEW_USD_LIMIT] = None
        elif is_add_chat_id:
            self.set_add_chat_id(update, context)
        else:
            update.message.reply_text('Please use a command. Type /help for a list of available commands.')
    
    def set_new_limit(self, update: Update, user_data, new_limit, is_usd=False):
        if is_usd:
            self.set_new_usd_limit(update, user_data, new_limit)
        else:
            self.set_new_message_limit(update, user_data, new_limit)
            
    def set_new_usd_limit(self, update: Update, user_data, new_limit):
        chat_id = user_data[self.fin_constants.IS_TO_SET_NEW_USD_LIMIT]
        self.financial_validator.set_limit(chat_id, new_limit)
        limit_msg = f"The bot's daily limit for your chat has been set to {new_limit} USD."
        update.message.reply_text(limit_msg)

            
    def set_new_message_limit(self, update: Update, user_data, new_limit):
        chat_id = user_data[self.constants.IS_TO_SET_NEW_LIMIT]
        self.message_limit_handler.set_limit(chat_id, new_limit)
        limit_msg = f"The bot's daily message limit for your chat has been set to {new_limit}."
        update.message.reply_text(limit_msg)
        
    def set_add_chat_id(self, update: Update, context: CallbackContext):
        user_data = context.user_data
        chat_id_str = update.message.text

        if re.match(r'^-?\d+$', chat_id_str):
            dest_group_chat_id = int(chat_id_str)
            chat_id = user_data[self.constants.ADD_CHAT_ID]

            # Convert dest_group_chat_id to an integer if it is a string
            if isinstance(dest_group_chat_id, str) and (dest_group_chat_id.isdigit() or (dest_group_chat_id.startswith('-') and dest_group_chat_id[1:].isdigit())):
                dest_group_chat_id = int(dest_group_chat_id)

            # Compare the chat IDs
            if chat_id == dest_group_chat_id:
                update.message.reply_text("The chat ID and the destination group chat ID cannot be the same.")
            else:
                self.admin_notification_chat_map[chat_id] = dest_group_chat_id
                update.message.reply_text(f"Chat ID {dest_group_chat_id} will receive notifications from group chat {chat_id}.")
        else:
            update.message.reply_text("Please provide a valid integer value for the chat ID.")
        user_data[self.constants.ADD_CHAT_ID] = None
        
    def get_admin_notification_chat_id(self, chat_id: int):
        return self.admin_notification_chat_map.get(chat_id)
    
    def toggle_admin_notifications(self, chat_id: int):
        if chat_id in self.silenced_notifications:
            del self.silenced_notifications[chat_id]
        else:
            self.silenced_notifications[chat_id] = True

    def admin_notifications_enabled(self, chat_id: int) -> bool:
        return chat_id not in self.silenced_notifications
