import time


class Logger:
	def __init__(self, name=None, thread=None, file_name=None, display_debug=False):
		self.name = name
		self.thread = thread
		self.file_name = file_name
		self.display_debug = display_debug

	def _log(self, msg, log_type):
		if not isinstance(msg, str):
			msg = str(msg)
		message = '[{} {}]'.format(format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))), log_type)
		if self.name is not None:
			message += ' [{}]'.format(self.name)
		if self.thread is not None:
			message += ' [Thread {}]'.format(self.thread)
		message += ' {}\n'.format(msg)
		print(message, end='')
		if self.file_name is not None:
			try:
				with open(self.file_name, 'a') as f:
					f.write(message)
			except Exception as e:
				print('fail to write log to file "{}"'.format(self.file_name))
				print(e.args)

	def log(self, msg, log_type=None):
		if log_type is None:
			self.info(msg)
		else:
			self.log(msg, log_type)

	def info(self, msg):
		self._log(msg, 'INFO')

	def debug(self, msg):
		if self.display_debug:
			self._log(msg, 'DEBUG')

	def warn(self, msg):
		self._log(msg, 'WARN')

	def error(self, msg):
		self._log(msg, 'ERROR')
