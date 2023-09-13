import time

class MessageLimitHandler:
    """
    A class for handling message limits for GPTBot.
    """
    def __init__(self):
        self.sent_messages = {}
        self.reset_times = {}
        self.message_limits = {}
        self.reset_interval = 24 * 60 * 60  # 24 hours in seconds

    def set_limit(self, chat_id, limit):
        self.message_limits[chat_id] = limit

    def _remove_key(self, dictionary, key):
        if key in dictionary:
            del dictionary[key]

    def remove_limit(self, chat_id):
        self._remove_key(self.message_limits, chat_id)
        self._remove_key(self.sent_messages, chat_id)
        self._remove_key(self.reset_times, chat_id)

    def get_limit(self, chat_id):
        return self.message_limits.get(chat_id, None)
    
    def has_limit(self, chat_id):
        return chat_id in self.message_limits

    def register_message(self, chat_id):
        if not self.has_limit(chat_id):
            return
        
        current_time = time.time()

        if chat_id not in self.sent_messages:
            self.sent_messages[chat_id] = 0

        if chat_id not in self.reset_times:
            self.reset_times[chat_id] = current_time

        # Check if the reset interval has passed and reset the sent messages and reset times if needed
        if current_time - self.reset_times[chat_id] > self.reset_interval:
            self.sent_messages[chat_id] = 0
            self.reset_times[chat_id] = current_time

        # Increment the sent message count for this chat
        self.sent_messages[chat_id] += 1

    def is_within_message_limit(self, chat_id):
        if chat_id not in self.message_limits:
            return True

        messages_sent = self.sent_messages.get(chat_id, 0)
        return messages_sent < self.message_limits[chat_id]

    def get_remaining_messages(self, chat_id):
        messages_sent = self.sent_messages.get(chat_id, 0)
        limit = self.message_limits.get(chat_id)

        if limit is not None:
            return max(limit - messages_sent, 0)

        return float("inf")
    
    def can_send_message(self, chat_id):
        if not self.has_limit(chat_id):
            return True

        if self.is_within_message_limit(chat_id):
            return True

        return False