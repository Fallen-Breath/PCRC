import os
import sys
import time
import zipfile
from logging import Logger, Formatter, StreamHandler, INFO, FileHandler, DEBUG

from colorlog import ColoredFormatter

from pcrc.utils import file_util


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
	FILE_FMT = Formatter('[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
	CONSOLE_FMT = ColoredFormatter(
		'[%(asctime)s] [%(threadName)s/%(log_color)s%(levelname)s%(reset)s]: %(message_log_color)s%(message)s%(reset)s',
		log_colors=LOG_COLORS,
		secondary_log_colors=SECONDARY_LOG_COLORS,
		datefmt='%H:%M:%S'
	)

	def __init__(self):
		super().__init__('PCRC')
		self.file_handler = None

		self.console_handler = StreamHandler(sys.stdout)
		self.console_handler.setFormatter(self.CONSOLE_FMT)

		self.addHandler(self.console_handler)
		self.setLevel(DEBUG)

	def set_file(self, file_name: str):
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
