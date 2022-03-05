import json


DefaultOption = {
	"__1__": "-------- Base --------",
	"language": "en_us",
	"debug_mode": False,

	"__2__": "-------- Account and Server --------",
	"online_mode": False,
	"authenticate_type": "mojang",
	"username": "bot_PCRC",
	"password": "secret",
	"address": "localhost",
	"port": 20000,
	"server_name": "SECRET SERVER",
	"initial_version": "1.14.4",

	"__3__": "-------- PCRC Control --------",
	"file_size_limit_mb": 2048,
	"file_buffer_size_mb": 8,
	"time_recorded_limit_hour": 12,
	"delay_before_afk_second": 15,
	"record_packets_when_afk": True,
	"auto_relogin": True,
	"chat_spam_protect": True,
	"command_prefix": "!!PCRC",

	"__4__": "-------- PCRC Features --------",
	"minimal_packets": True,
	"daytime": 4000,
	"weather": False,
	"with_player_only": True,
	"remove_items": False,
	"remove_bats": True,
	"remove_phantoms": True,

	"__5__": "-------- PCRC Whitelist --------",
	"enabled": False,
	"whitelist": [
		"Fallen_Breath",
		"Steve"
	]
}

SettableOptions = [
	'language',
	'server_name',
	'minimal_packets',
	'daytime',
	'weather',
	'with_player_only',
	'remove_items',
	'remove_bats',
	'remove_phantoms',
	'file_size_limit_mb',
	'time_recorded_limit_hour',
]


CONFIG_FILE = 'config.json'


class Config:
	def __init__(self):
		try:
			with open(CONFIG_FILE, 'r', encoding='utf8') as f:
				self.data = json.load(f)
		except FileNotFoundError:
			self.data = {}
		self.fill_missing_options()
		self.write_to_file()

	def fill_missing_options(self):
		new_data = {}
		for key in DefaultOption.keys():
			new_data[key] = self.data.get(key, DefaultOption[key])
		self.data = new_data

	def get_option_type(self, option):
		return type(self.data[option])

	def convert_to_option_type(self, option, value):
		t = self.get_option_type(option)
		if t == bool:
			value = value in ['True', 'true', 'TRUE', True] or (type(value) is int and value != 0)
		else:
			value = t(value)
		return value

	def set_value(self, option, value, forced=False):
		if not forced:
			value = self.convert_to_option_type(option, value)
		self.data[option] = value
		return

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
			return None

	def display(self):
		def secret(text):
			return '******' if len(text) <= 4 else '{}***{}'.format(text[0:2], text[-1])
		messages = [
			'================ Config ================',
			'-------- Base --------',
			f"Language = {self.get('language')}",
			f"Debug mode = {self.get('debug_mode')}",
			'-------- Account and Server --------',
			f"Online mode = {self.get('online_mode')}",
			f"User name = {secret(self.get('username'))}",
			f"Password = ******",
			f"Server address = {self.get('address')}",
			f"Server port = {self.get('port')}",
			f"Server name = {self.get('server_name')}",
			f"Initial Version = {self.get('initial_version')}",
			'-------- PCRC Control --------',
			f"File size limit = {self.get('file_size_limit_mb')}MB",
			f"File buffer size = {self.get('file_buffer_size_mb')}MB",
			f"Time recorded limit = {self.get('time_recorded_limit_hour')}h",
			f"Auto relogin = {self.get('auto_relogin')}",
			f"Chat spam protect = {self.get('chat_spam_protect')}",
			'-------- PCRC Features --------',
			f"Minimal packets mode = {self.get('minimal_packets')}",
			f"Daytime set to = {self.get('daytime')}",
			f"Weather switch = {self.get('weather')}",
			f"Record with player only = {self.get('with_player_only')}",
			f"Remove items = {self.get('remove_items')}",
			f"Remove bats = {self.get('remove_bats')}",
			f"Remove phantoms = {self.get('remove_phantoms')}",
			'========================================',
			'-------- Whitelist --------',
			f"Whitelist = {self.get('enabled')}",
			f"Whitelist player(s) = {self.get('whitelist')}"
		]
		return '\n'.join(messages)
