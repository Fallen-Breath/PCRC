import os
import time
import traceback


class Logger:
	DefaultFileName = './log/PCRC.log'

	def __init__(self, name=None, thread=None, file_name=DefaultFileName, display_debug=False):
		self.name = name
		self.thread = thread
		self.file_name = file_name
		self.display_debug = display_debug
		if not os.path.isdir(os.path.dirname(file_name)):
			os.makedirs(os.path.dirname(file_name))

	@staticmethod
	def set_default_file_name(fn):
		Logger.DefaultFileName = fn

	def _log(self, msg, log_type, do_print):
		if not isinstance(msg, str):
			msg = str(msg)
		message = '[{} {}]'.format(format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))), log_type)
		if self.name is not None:
			message += ' [{}]'.format(self.name)
		if self.thread is not None:
			message += ' [Thread {}]'.format(self.thread)
		message += ' {}\n'.format(msg)
		if do_print:
			print(message, end='')
		if self.file_name is not None:
			try:
				with open(self.file_name, 'a') as f:
					f.write(message)
			except Exception:
				print('fail to write log to file "{}"'.format(self.file_name))
				print(traceback.format_exc())

	def log(self, msg, log_type=None, do_print=True):
		if log_type is None:
			self.info(msg, do_print)
		else:
			self._log(msg, log_type, do_print)

	def info(self, msg, do_print=True):
		self._log(msg, 'INFO', do_print)

	def debug(self, msg, do_print=True):
		if self.display_debug:
			self._log(msg, 'DEBUG', do_print)

	def warn(self, msg, do_print=True):
		self._log(msg, 'WARN', do_print)

	def error(self, msg, do_print=True):
		self._log(msg, 'ERROR', do_print)
