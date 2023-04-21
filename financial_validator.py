import time

class FinancialValidator:
    """
    A class for validating financial-related input for GPTBot.
    """
    def __init__(self):
        self.spent_tokens = {}
        self.reset_times = {}
        self.dollar_limits = {}
        self.reset_interval = 24 * 60 * 60  # 24 hours in seconds
        self.price_per_token = 0.2  # Price per token in USD

    def set_limit(self, chat_id, limit):
        self.dollar_limits[chat_id] = limit

    def remove_limit(self, chat_id):
        self._remove_data(chat_id, self.dollar_limits)
        self._remove_data(chat_id, self.spent_tokens)
        self._remove_data(chat_id, self.reset_times)

    def _remove_data(self, chat_id, data_dict):
        if chat_id in data_dict:
            del data_dict[chat_id]

    def get_limit(self, chat_id):
        return self.dollar_limits.get(chat_id, None)

    def register_tokens(self, chat_id, tokens):
        current_time = time.time()

        self._initialize_chat_data(chat_id, self.spent_tokens, 0)
        self._initialize_chat_data(chat_id, self.reset_times, current_time)

        self._reset_spent_tokens_if_interval_passed(chat_id, current_time)

        self.spent_tokens[chat_id] += tokens

    def _initialize_chat_data(self, chat_id, data_dict, default_value):
        if chat_id not in data_dict:
            data_dict[chat_id] = default_value

    def _reset_spent_tokens_if_interval_passed(self, chat_id, current_time):
        # Check if the reset interval has passed
        if current_time - self.reset_times[chat_id] > self.reset_interval:
            # Reset spent tokens and set the new reset time for the chat
            self.spent_tokens[chat_id] = 0
            self.reset_times[chat_id] = current_time

    def is_spending_within_limit(self, chat_id):
        # If there's no limit set for the chat, spending is always within limit
        if chat_id not in self.dollar_limits:
            return True

        # Calculate the spent amount in USD
        spent_amount = self._calculate_spent_amount(chat_id)

        # Check if the spent amount is within the set dollar limit
        return spent_amount <= self.dollar_limits[chat_id]

    def _calculate_spent_amount(self, chat_id):
        # Get the number of spent tokens for the chat
        tokens_spent = self.spent_tokens.get(chat_id, 0)
        # Calculate the spent amount in USD
        return tokens_spent * self.price_per_token

    def left_dollar_usage(self, chat_id: int) -> float:
        # Calculate the spent amount in USD
        spent_amount = self._calculate_spent_amount(chat_id)
        # Get the dollar limit for the chat
        limit = self.dollar_limits.get(chat_id)

        # Calculate the remaining dollar usage and return it
        if limit is not None:
            return max(limit - spent_amount, 0)
        return float("inf")
    
    def has_limit(self, chat_id):
        return chat_id in self.dollar_limits

    def can_send_message(self, chat_id):
        if not self.has_limit(chat_id):
            return True

        if self.is_spending_within_limit(chat_id):
            return True

        return False