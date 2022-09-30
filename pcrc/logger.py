import os
import sys
import time
import zipfile
from logging import Logger, Formatter, StreamHandler, INFO, FileHandler, DEBUG, Handler
from typing import Optional

from colorlog import ColoredFormatter

from pcrc.utils import file_util

LOG_FILE_PATH = 'logs/PCRC.log'


class PcrcLogger(Logger):
	LOG_COLORS = {
		'DEBUG': 'blue',
		'INFO': 'green',
		'WARNING': 'yellow',
		'ERROR': 'red',
		'CRITICAL': 'bold_red',
	}
	SECONDARY_LOG_COLORS = {
		'message': {
			'WARNING': 'yellow',
			'ERROR': 'red',
			'CRITICAL': 'red'
		}
	}
	FILE_FMT = Formatter('[%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

	def __init__(self):
		super().__init__('PCRC')
		self.console_handler: Optional[Handler] = None
		self.file_handler: Optional[Handler] = None

		self.set_console_handler(StreamHandler(sys.stdout))
		self.set_file_handler(LOG_FILE_PATH)

	def set_debug(self, show_debug: bool):
		self.setLevel(DEBUG if show_debug else INFO)

	def set_console_handler(self, console_handler: Handler):
		if self.console_handler is not None:
			self.removeHandler(self.console_handler)
		self.console_handler = console_handler
		self.set_console_logging_prefix(None)
		self.addHandler(self.console_handler)

	def set_console_logging_prefix(self, prefix: Optional[str]):
		fmt = '[%(asctime)s] [%(threadName)s/%(log_color)s%(levelname)s%(reset)s]: %(message_log_color)s%(message)s%(reset)s'
		if prefix is not None:
			fmt = '[{}] {}'.format(prefix, fmt)
		formatter = ColoredFormatter(fmt, log_colors=self.LOG_COLORS, secondary_log_colors=self.SECONDARY_LOG_COLORS, datefmt='%H:%M:%S')
		self.console_handler.setFormatter(formatter)

	def set_file_handler(self, file_name: str):
		if self.file_handler is not None:
			self.removeHandler(self.file_handler)
		file_util.touch_directory(os.path.dirname(file_name))
		if os.path.isfile(file_name):
			modify_time = time.strftime('%Y-%m-%d', time.localtime(os.stat(file_name).st_mtime))
			counter = 0
			while True:
				counter += 1
				zip_file_name = '{}/{}-{}.zip'.format(os.path.dirname(file_name), modify_time, counter)
				if not os.path.isfile(zip_file_name):
					break
			zipf = zipfile.ZipFile(zip_file_name, 'w')
			zipf.write(file_name, arcname=os.path.basename(file_name), compress_type=zipfile.ZIP_DEFLATED)
			zipf.close()
			os.remove(file_name)
		self.file_handler = FileHandler(file_name, encoding='utf8')
		self.file_handler.setFormatter(self.FILE_FMT)
		self.addHandler(self.file_handler)

	def close_file(self):
		if self.file_handler is not None:
			self.removeHandler(self.file_handler)
			self.file_handler.close()
			self.file_handler = None
