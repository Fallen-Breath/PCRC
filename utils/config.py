import json


DefaultOption = json.loads('''
{
	"__1__": "-------- Base --------",
	"language": "en_us",
	"debug_mode": false,

	"__2__": "-------- Account and Server --------",
	"online_mode": false,
	"yggdrasil_server": "",
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
	"record_packets_when_afk": true,
	"auto_relogin": true,
	"chat_spam_protect": true,
	"command_prefix": "!!PCRC",

	"__4__": "-------- PCRC Features --------",
	"minimal_packets": true,
	"daytime": 4000,
	"weather": false,
	"with_player_only": true,
	"remove_items": false,
	"remove_bats": true,
	"remove_phantoms": true,

	"__5__": "-------- PCRC Whitelist --------",
	"enabled": false,
	"whitelist": [
		"Fallen_Breath",
		"Steve"
	]
}
''')

SettableOptions = [
	'language',
	'yggdrasil_server',
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


class Config:
	def __init__(self, file_name):
		self.file_name = file_name
		try:
			with open(file_name) as f:
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

	def write_to_file(self, file_name=None):
		if file_name is None:
			file_name = self.file_name
		text = json.dumps(self.data, indent=4)
		for key in self.data.keys():
			if len(key) == 5 and key[0] == key[1] == key[3] == key[4] == '_' and key != '__1__':
				p = text.find('    "{}"'.format(key))
				text = text[:p] + '\n' + text[p:]
		with open(file_name, 'w') as f:
			f.write(text)

	def get(self, option):
		if option in self.data:
			return self.data[option]
		else:
			return None

	def display(self):
		def secret(text):
			return  '******' if len(text) <= 4 else '{}***{}'.format(text[0:2], text[-1])
		messages = []
		messages.append('================ Config ================')
		messages.append('-------- Base --------')
		messages.append(f"Language = {self.get('language')}")
		messages.append(f"Debug mode = {self.get('debug_mode')}")
		messages.append('-------- Account and Server --------')
		messages.append(f"Online mode = {self.get('online_mode')}")
		messages.append(f"Yggdrasil server = {self.get('yggdrasil_server')}")
		messages.append(f"User name = {secret(self.get('username'))}")
		messages.append(f"Password = ******")
		messages.append(f"Server address = {self.get('address')}")
		messages.append(f"Server port = {self.get('port')}")
		messages.append(f"Server name = {self.get('server_name')}")
		messages.append(f"Initial Version = {self.get('initial_version')}")
		messages.append('-------- PCRC Control --------')
		messages.append(f"File size limit = {self.get('file_size_limit_mb')}MB")
		messages.append(f"File buffer size = {self.get('file_buffer_size_mb')}MB")
		messages.append(f"Time recorded limit = {self.get('time_recorded_limit_hour')}h")
		messages.append(f"Auto relogin = {self.get('auto_relogin')}")
		messages.append(f"Chat spam protect = {self.get('chat_spam_protect')}")
		messages.append('-------- PCRC Features --------')
		messages.append(f"Minimal packets mode = {self.get('minimal_packets')}")
		messages.append(f"Daytime set to = {self.get('daytime')}")
		messages.append(f"Weather switch = {self.get('weather')}")
		messages.append(f"Record with player only = {self.get('with_player_only')}")
		messages.append(f"Remove items = {self.get('remove_items')}")
		messages.append(f"Remove bats = {self.get('remove_bats')}")
		messages.append(f"Remove phantoms = {self.get('remove_phantoms')}")
		messages.append('========================================')
		messages.append('-------- Whitelist --------')
		messages.append(f"Whitelist = {self.get('enabled')}")
		messages.append(f"Whitelist player(s) = {self.get('whitelist')}")
		return '\n'.join(messages)
