import json
from typing import Type, Any

from pcrc.utils import resources_util

SettableOptions = [
	'language',
	'server_name',
	'daytime',
	'weather',
	'with_player_only',
	'remove_items',
	'remove_bats',
	'remove_phantoms',
	'file_size_limit_mb',
	'time_recorded_limit_hour',
]

DEFAULT_CONFIG = json.loads(resources_util.get_data('resources/default_config.json'))
CONFIG_FILE = 'config.json'


class Config:
	data: dict

	def __init__(self):
		self.was_missing_file = False
		self.__load()

	def __load(self):
		self.was_missing_file = False
		try:
			with open(CONFIG_FILE, 'r', encoding='utf8') as f:
				self.data = json.load(f)
		except FileNotFoundError:
			self.data = {}
			self.was_missing_file = True
		self.fill_missing_options()
		self.write_to_file()

	def reload(self):
		self.__load()

	def fill_missing_options(self):
		new_data = {}
		for key in DEFAULT_CONFIG.keys():
			new_data[key] = self.data.get(key, DEFAULT_CONFIG[key])
		self.data = new_data

	def get_option_type(self, option) -> Type:
		return type(self.data[option])

	def convert_to_option_type(self, option: str, value: Any) -> Any:
		t = self.get_option_type(option)
		if t == bool:
			value = value in ['True', 'true', 'TRUE', True] or (type(value) is int and value != 0)
		else:
			value = t(value)
		return value

	def set_value(self, option: str, value: Any, forced: bool = False):
		if not forced:
			value = self.convert_to_option_type(option, value)
		self.data[option] = value

	def write_to_file(self):
		text = json.dumps(self.data, indent=4)
		for key in self.data.keys():
			if len(key) == 5 and key[0] == key[1] == key[3] == key[4] == '_' and key != '__1__':
				p = text.find('    "{}"'.format(key))
				text = text[:p] + '\n' + text[p:]
		with open(CONFIG_FILE, 'w', encoding='utf8') as f:
			f.write(text)

	def get(self, option: str):
		if option in self.data:
			return self.data[option]
		else:
			raise KeyError('Unknown option name: {}'.format(option))
