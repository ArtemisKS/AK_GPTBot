import threading
import openai
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

from financial_validator import FinancialValidator
from message_limit_handler import MessageLimitHandler
from admin_menu_manager import AdminMenuManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GPTBot:
    def __init__(self, telegram_api_key, gpt_api_key):
        self.TELEGRAM_API_KEY = telegram_api_key
        self.GPT_API_KEY = gpt_api_key

        self.updater = Updater(self.TELEGRAM_API_KEY)
        self.financial_validator = FinancialValidator()
        self.message_limit_handler = MessageLimitHandler()
        self.admin_menu_manager = AdminMenuManager(self.message_limit_handler, self.financial_validator)
        
        # Initialize OpenAI API
        openai.api_key = self.GPT_API_KEY

    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            'Hello! I am a GPT-4 bot. Type /gpt followed by your question!',
            reply_markup=ReplyKeyboardRemove()
        )

    def send_typing_action(self, chat_id, stop_typing_event, context):
        while not stop_typing_event.is_set():
            context.bot.send_chat_action(chat_id=chat_id, action='typing')
            stop_typing_event.wait(5)

    def gpt(self, update: Update, context: CallbackContext):
        if len(context.args) > 0:
            chat_id = update.effective_chat.id

            if not self.financial_validator.can_send_message(chat_id):
                update.message.reply_text('The daily USD limit for GPT usage has been reached. Please try again later.')
                return
            elif not self.message_limit_handler.can_send_message(chat_id):
                update.message.reply_text('The daily limit GPT usage has been reached. Please try again later.')
                return

            question = ' '.join(context.args)

            # Create an event to stop the typing action when the response is received
            stop_typing_event = threading.Event()

            # Start a separate thread to send the typing action
            typing_thread = threading.Thread(target=self.send_typing_action, args=(chat_id, stop_typing_event, context))
            typing_thread.start()

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant, named Averiy (рус. Аверий)"},
                    {"role": "user", "content": f"{question}\n\nAnswer:"}
                ])
            
            tokens_used = response["usage"]["total_tokens"]
            logging.info(f'{tokens_used} total tokens used.')
            
            # Register the message in the MessageLimitHandler
            self.message_limit_handler.register_message(chat_id)
            # Register the message in the FinancialValidator
            self.financial_validator.register_tokens(chat_id, tokens_used)

            if not self.financial_validator.is_spending_within_limit(chat_id):
                self.notify_admins_limit_reached(chat_id, "USD", context)
            elif not self.message_limit_handler.is_within_message_limit(chat_id):
                self.notify_admins_limit_reached(chat_id, "messages", context)

            # Set the event to stop the typing action
            stop_typing_event.set()

            answer_text = response.choices[0].message.content.strip()
            update.message.reply_text(answer_text)
        else:
            update.message.reply_text('Please provide a question after the /gpt command.')

    def notify_admins_limit_reached(self, chat_id: int, limit_type: str, context: CallbackContext):
        if not self.admin_menu_manager.admin_notifications_enabled(chat_id):
            return

        dest_chat_id = self.admin_menu_manager.get_admin_notification_chat_id(chat_id)
        if dest_chat_id:
            message = f"The {limit_type} limit has been reached in chat ID {chat_id}."
            self.updater.bot.send_message(chat_id=dest_chat_id, text=message)
        else:
            message = f"No destination chat ID to receive notifications from the current chat: {chat_id}"
            logging.info(message)

    def help_command(self, update: Update, context: CallbackContext):
        help_text = '''Available commands:
        /start - Start the bot
        /gpt [question] - Get an answer from GPT-4
        /help - Show this help message
        /adminmenu - Access admin-only commands and settings
        '''
        update.message.reply_text(help_text)

    def unknown_command(self, update: Update, context: CallbackContext):
        update.message.reply_text('Unknown command. Type /help for a list of available commands.')

    def run(self):
        dp = self.updater.dispatcher

        dp.add_handler(CommandHandler('start', self.start))
        dp.add_handler(CommandHandler('gpt', self.gpt, pass_args=True))
        dp.add_handler(CommandHandler('help', self.help_command))
        dp.add_handler(CommandHandler('adminmenu', self.admin_menu_manager.show_admin_menu))
        dp.add_handler(CallbackQueryHandler(self.admin_menu_manager.handle_admin_callback))
        dp.add_handler(MessageHandler(Filters.command, self.unknown_command))
        dp.add_handler(MessageHandler(Filters.text & (~Filters.command), self.admin_menu_manager.handle_text))

        self.updater.start_polling()
        self.updater.idle()


# Set your API keys as environment variables
TELEGRAM_API_KEY = '6233026479:AAHXouIRHy2fpQZdih6xchzDrIphxViUQbY' #os.getenv('TELEGRAM_API_KEY')
GPT_API_KEY = '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' #os.getenv('GPT_API_KEY')

if __name__ == '__main__':
    gpt_bot = GPTBot(TELEGRAM_API_KEY, GPT_API_KEY)
    gpt_bot.run()
