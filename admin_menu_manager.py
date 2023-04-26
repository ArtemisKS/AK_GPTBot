import re
import logging
from collections import namedtuple
from telegram.ext import CallbackContext
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.error import Unauthorized
from localization import loc

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
        "GET_CHAT_ID",
        "GROUP_CHAT_ID",
        "BOT_DESC",
        "REMOVE_BOT_DESC",
        "SHOW_BOT_DESC"
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
        
        self.bot_descriptions = {}
        
        # Initialize constants
        self.constants = self.Constants(
            SET_NEW_LIMIT="set_new_limit",
            REMOVE_LIMIT="remove_limit",
            SHOW_LIMIT="show_limit",
            SHOW_REMAINING_MESSAGES="show_remaining_messages",
            IS_TO_SET_NEW_LIMIT="is_to_set_new_limit",
            TOGGLE_NOTIFICATIONS="toggle_notifications",
            ADD_CHAT_ID="add_chat_id",
            GET_CHAT_ID="get_chat_id",
            GROUP_CHAT_ID="chat_id",
            BOT_DESC="bot_description",
            REMOVE_BOT_DESC="remove_bot_description",
            SHOW_BOT_DESC="show_bot_description"
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
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        self.display_admin_menu(user_id, chat_id, update, context)

    def show_admin_menu_callback(self, query: CallbackQuery, context: CallbackContext, original_chat_id=None):
        user_id = query.from_user.id
        chat_id = original_chat_id if original_chat_id else query.message.chat.id
        
        self.display_admin_menu(user_id, chat_id, query, context)

    def display_admin_menu(self, user_id: int, chat_id: int, update: Update, context: CallbackContext):
        query = None
        
        if isinstance(update, CallbackQuery):
            query = update
        
        context.user_data[user_id] = {self.constants.GROUP_CHAT_ID: chat_id}  # Store chat_id in context.user_data

        if self.is_user_admin(user_id, chat_id, context):
            keyboard = [
                [InlineKeyboardButton(loc('set_messages_limit'), callback_data=self.constants.SET_NEW_LIMIT),
                InlineKeyboardButton(loc('set_dollar_limit'), callback_data=self.fin_constants.SET_NEW_DOLLAR_LIMIT)],
                [InlineKeyboardButton(loc('show_messages_limit'), callback_data=self.constants.SHOW_LIMIT),
                InlineKeyboardButton(loc('show_dollar_limit'), callback_data=self.fin_constants.SHOW_DOLLAR_LIMIT)],
                [InlineKeyboardButton(loc('remove_messages_limit'), callback_data=self.constants.REMOVE_LIMIT),
                InlineKeyboardButton(loc('remove_dollar_limit'), callback_data=self.fin_constants.REMOVE_DOLLAR_LIMIT)],
                [InlineKeyboardButton(loc('messages_left'), callback_data=self.constants.SHOW_REMAINING_MESSAGES),
                InlineKeyboardButton(loc('dollars_left'), callback_data=self.fin_constants.SHOW_REMAINING_DOLLARS)],
                [InlineKeyboardButton(loc('set_bot_description'), callback_data=self.constants.BOT_DESC),
                 InlineKeyboardButton(loc('remove_bot_description'), callback_data=self.constants.REMOVE_BOT_DESC)],
                [InlineKeyboardButton(loc('show_bot_description'), callback_data=self.constants.SHOW_BOT_DESC)],
                [InlineKeyboardButton(loc('add_chat_id'), callback_data=self.constants.ADD_CHAT_ID)],
                [InlineKeyboardButton(loc('get_current_chat_id'), callback_data=self.constants.GET_CHAT_ID)]
            ]

            silence_button_text = loc('mute_notifications') if self.admin_notifications_enabled(chat_id) else loc('unmute_notifications')
            keyboard.append([InlineKeyboardButton(silence_button_text, callback_data=self.constants.TOGGLE_NOTIFICATIONS)])

            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                context.bot.send_message(chat_id=user_id, text=f"{loc('admin_menu')}:", reply_markup=reply_markup)
            except Unauthorized:
                error_message = loc('start_conversation')
                # Send an inline query answer if the bot can't initiate a conversation
                if query:
                    query.answer(error_message)
                else:
                    update.message.reply_text(error_message)
        else:
            error_message = loc('admin_only')
            if query:
                query.answer(error_message)
            else:
                update.message.reply_text(error_message)
        
    def handle_admin_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        user = query.from_user
        data = query.data
        
        if user.id in context.user_data and self.constants.GROUP_CHAT_ID in context.user_data[user.id]:
            chat_id = context.user_data[user.id][self.constants.GROUP_CHAT_ID]  # Retrieve chat_id from context.user_data
        else:
            query.answer(loc('error_chat_id_not_found'))
            return

        if self.is_user_admin(user.id, chat_id, context):
            if data == self.constants.SET_NEW_LIMIT:
                self.set_new_limit_callback(query, context, chat_id)
            elif data == self.constants.REMOVE_LIMIT:
                self.remove_limit_callback(query, context, chat_id)
            elif data == self.constants.SHOW_LIMIT:
                self.show_limit_callback(query, context, chat_id)
            elif data == self.constants.SHOW_REMAINING_MESSAGES:
                self.show_remaining_messages_callback(query, context, chat_id)
            elif data == self.fin_constants.SET_NEW_DOLLAR_LIMIT:
                self.set_new_usd_limit_callback(query, context, chat_id)
            elif data == self.fin_constants.REMOVE_DOLLAR_LIMIT:
                self.remove_usd_limit_callback(query, context, chat_id)
            elif data == self.fin_constants.SHOW_DOLLAR_LIMIT:
                self.show_usd_limit_callback(query, context, chat_id)
            elif data == self.fin_constants.SHOW_REMAINING_DOLLARS:
                self.show_remaining_usd_callback(query, context, chat_id)
            elif data == self.constants.TOGGLE_NOTIFICATIONS:
                self.toggle_admin_notifications(chat_id)
                self.show_admin_menu_callback(query, context, original_chat_id=chat_id)
            elif data == self.constants.ADD_CHAT_ID:
                self.handle_add_chat_id(query, context, chat_id)
            elif data == self.constants.GET_CHAT_ID:
                self.get_current_chat_id_callback(query, context, chat_id)
            elif data == self.constants.BOT_DESC:
                self.set_new_bot_description_callback(query, context, chat_id)
            elif data == self.constants.REMOVE_BOT_DESC:
                self.remove_bot_description_callback(query, context, chat_id)
            elif data == self.constants.SHOW_BOT_DESC:
                self.show_bot_description_callback(query, context, chat_id)
        else:
            query.answer(loc('admin_required'))

    def get_current_chat_id_callback(self, query, context: CallbackContext, chat_id: int):
        message = f"Current chat ID: {chat_id}"
        logging.info(message)
        query.answer(message)

    def handle_add_chat_id(self, query, context: CallbackContext, chat_id: int):
        user_id = query.from_user.id

        context.user_data[self.constants.ADD_CHAT_ID] = chat_id
        context.bot.send_message(
            chat_id=query.from_user.id,
            text=loc('enter_dest_chat_id')
            )

    def set_new_limit_callback(self, query, context: CallbackContext, chat_id: int):
        context.user_data[self.constants.IS_TO_SET_NEW_LIMIT] = chat_id
        context.bot.send_message(chat_id=query.from_user.id, text=loc('enter_new_message_limit'))

    def remove_limit_callback(self, query, context: CallbackContext, chat_id: int):
        if self.message_limit_handler.has_limit(chat_id):
            self.message_limit_handler.remove_limit(chat_id)
            context.bot.send_message(chat_id=query.from_user.id, text=loc('message_limit_removed'))
        else:
            context.bot.send_message(chat_id=query.from_user.id, text=loc('no_message_limit_set'))

    def show_limit_callback(self, query, context: CallbackContext, chat_id: int):
        if self.message_limit_handler.has_limit(chat_id):
            limit = self.message_limit_handler.get_limit(chat_id)
            context.bot.send_message(chat_id=query.from_user.id, text=loc('daily_message_limit', limit=limit))
        else:
            context.bot.send_message(chat_id=query.from_user.id, text=loc('no_message_limit_set'))

    def show_remaining_messages_callback(self, query, context: CallbackContext, chat_id: int):
        if not self.message_limit_handler.has_limit(chat_id):
            context.bot.send_message(chat_id=query.from_user.id, text=loc('no_remaining_message_limit'))
        else:
            remaining_messages = self.message_limit_handler.get_remaining_messages(chat_id)
            context.bot.send_message(chat_id=query.from_user.id, text=loc('remaining_messages', remaining_messages=remaining_messages))

    def set_new_usd_limit_callback(self, query, context: CallbackContext, chat_id: int):
        context.user_data[self.fin_constants.IS_TO_SET_NEW_USD_LIMIT] = chat_id
        context.bot.send_message(chat_id=query.from_user.id, text=loc('enter_new_usd_limit'))

    def remove_usd_limit_callback(self, query, context: CallbackContext, chat_id: int):
        self.financial_validator.remove_limit(chat_id)
        context.bot.send_message(chat_id=query.from_user.id, text=loc('daily_usd_limit_removed'))

    def show_usd_limit_callback(self, query, context: CallbackContext, chat_id: int):
        limit = self.financial_validator.get_limit(chat_id)
        if limit is not None:
            context.bot.send_message(chat_id=query.from_user.id, text=loc('daily_usd_limit', limit=limit))
        else:
            context.bot.send_message(chat_id=query.from_user.id, text=loc('no_daily_usd_limit_set'))

    def show_remaining_usd_callback(self, query, context: CallbackContext, chat_id: int):
        if not self.financial_validator.has_limit(chat_id):
            message = loc('no_usd_limit')
        else:
            remaining_dollars = self.financial_validator.left_dollar_usage(chat_id)
            message = loc('remaining_usd_limit', remaining_dollars=int(remaining_dollars))

        context.bot.send_message(chat_id=query.from_user.id, text=message)
        
    def set_new_bot_description_callback(self, query, context: CallbackContext, chat_id: int):
        context.user_data[self.constants.BOT_DESC] = chat_id
        context.bot.send_message(chat_id=query.from_user.id, text=loc('enter_bot_description'))
        
    def remove_bot_description_callback(self, query, context: CallbackContext, chat_id: int):
        if self.bot_descriptions.get(chat_id):
            del self.bot_descriptions[chat_id]
            context.bot.send_message(chat_id=query.from_user.id, text=loc('bot_description_removed'))
        else:
            context.bot.send_message(chat_id=query.from_user.id, text=loc('no_custom_bot_description_set'))
            
    def show_bot_description_callback(self, query, context: CallbackContext, chat_id: int):
        bot_description = self.get_bot_description(chat_id)
        context.bot.send_message(chat_id=query.from_user.id, text=loc('bot_description', bot_description=bot_description))
        
    def handle_text(self, update: Update, context: CallbackContext):
        user_data = context.user_data

        is_to_set_new_limit = user_data.get(self.constants.IS_TO_SET_NEW_LIMIT)
        is_to_set_new_usd_limit = user_data.get(self.fin_constants.IS_TO_SET_NEW_USD_LIMIT)
        is_add_chat_id = user_data.get(self.constants.ADD_CHAT_ID)
        is_set_bot_desc = user_data.get(self.constants.BOT_DESC)

        if is_to_set_new_limit or is_to_set_new_usd_limit:
            new_limit_str = update.message.text
            if new_limit_str.isdigit():
                new_limit = int(new_limit_str)
                if is_to_set_new_limit:
                    self.set_new_limit(update, user_data, new_limit, is_usd=False)
                elif is_to_set_new_usd_limit:
                    self.set_new_limit(update, user_data, new_limit, is_usd=True)
            else:
                update.message.reply_text(loc('provide_valid_integer'))
            del user_data[self.constants.IS_TO_SET_NEW_LIMIT]
            del user_data[self.fin_constants.IS_TO_SET_NEW_USD_LIMIT]
        elif is_add_chat_id:
            self.set_add_chat_id(update, user_data)
        elif is_set_bot_desc:
            self.save_bot_description(update, user_data)
    
    def set_new_limit(self, update: Update, user_data, new_limit, is_usd=False):
        if is_usd:
            self.set_new_usd_limit(update, user_data, new_limit)
        else:
            self.set_new_message_limit(update, user_data, new_limit)
            
    def set_new_usd_limit(self, update: Update, user_data, new_limit):
        chat_id = user_data[self.fin_constants.IS_TO_SET_NEW_USD_LIMIT]
        self.financial_validator.set_limit(chat_id, new_limit)
        limit_msg = loc('daily_limit_set', new_limit=new_limit)
        update.message.reply_text(limit_msg)
            
    def set_new_message_limit(self, update: Update, user_data, new_limit):
        chat_id = user_data[self.constants.IS_TO_SET_NEW_LIMIT]
        self.message_limit_handler.set_limit(chat_id, new_limit)
        limit_msg = loc('daily_message_limit_set', new_limit=new_limit)
        update.message.reply_text(limit_msg)
        
    def save_bot_description(self, update: Update, user_data):
        bot_desc = update.message.text
        chat_id = user_data[self.constants.BOT_DESC]
        self.bot_descriptions[chat_id] = bot_desc
        del user_data[self.constants.BOT_DESC]
        update.message.reply_text(loc('bot_description_set', bot_desc=bot_desc))
        
    def set_add_chat_id(self, update: Update, user_data):
        chat_id_str = update.message.text

        if re.match(r'^-?\d+$', chat_id_str):
            dest_group_chat_id = int(chat_id_str)
            chat_id = user_data[self.constants.ADD_CHAT_ID]

            # Convert dest_group_chat_id to an integer if it is a string
            if isinstance(dest_group_chat_id, str) and (dest_group_chat_id.isdigit() or (dest_group_chat_id.startswith('-') and dest_group_chat_id[1:].isdigit())):
                dest_group_chat_id = int(dest_group_chat_id)

            # Compare the chat IDs
            if chat_id == dest_group_chat_id:
                update.message.reply_text(loc('same_chat_id_error'))
            else:
                self.admin_notification_chat_map[chat_id] = dest_group_chat_id
                update.message.reply_text(loc('receive_notifications', dest_group_chat_id=dest_group_chat_id, chat_id=chat_id))
        else:
            update.message.reply_text(loc('provide_valid_chat_id'))
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

    def get_bot_description(self, chat_id: int) -> str:
        return self.bot_descriptions.get(chat_id) or loc('assistant_desc')