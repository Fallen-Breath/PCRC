class RetryCounter:
	def __init__(self, max_retries: int):
		"""
		:param max_retries: maximum retry amount before success. set it to -1 for unlimited retries
		"""
		self.max_retries = max_retries
		self.counter = 0

	def reset_counter(self):
		self.counter = 0

	def can_retry(self):
		return self.max_retries < 0 or self.counter < self.max_retries

	def consume_retry_attempt(self):
		self.counter += 1

	def set_max_retries(self, max_retries: int):
		self.max_retries = max_retries
