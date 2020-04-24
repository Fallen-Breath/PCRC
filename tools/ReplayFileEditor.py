# coding: utf8
import gc
import json
import os
import shutil
import struct
import sys
import zipfile
import collections

sys.path.append("../")
from utils.SARC.packet import Packet as SARCPacket
import utils.utils as utils


class Data:
	def __init__(self, time_stamp, packet_length, packet):
		self.time_stamp = time_stamp
		self.packet_length = packet_length
		self.packet = packet

WorkingDirectory = '__RFETMP__/'
TriggerAddingDeltaThreshold = 10000
protocol_map_name = None  # id -> name
protocol_map_id = None  # name -> id
target_tmcpr = None
temp_tmcpr = None

def prepare():
	global protocol_map_name, protocol_map_id, protocol_version, input_file_name
	input_file_name = None
	if len(sys.argv) >= 2:
		input_file_name = sys.argv[1]
	while True:
		if input_file_name is None:
			input_file_name = input('Input .mcpr file name (Example: "My_Recording.mcpr"): ')
		if os.path.isfile(input_file_name):
			break
		else:
			print('File "{}" not found'.format(input_file_name))
		input_file_name = None
	print('File Name = {}'.format(input_file_name))
	print('Cleaning')
	if os.path.isdir(WorkingDirectory):
		shutil.rmtree(WorkingDirectory)
	os.mkdir(WorkingDirectory)
	print('Extracting')
	zipf = zipfile.ZipFile(input_file_name)
	zipf.extractall(WorkingDirectory)
	zipf.close()
	print('Reading protocol')
	with open(WorkingDirectory + 'metaData.json') as f:
		protocol_version = json.load(f)["protocol"]
	print('Protocol version =', protocol_version)
	with open('../protocol.json', 'r') as f:
		protocol_map_name = {}
		protocol_map_id = {}
		for item in json.load(f)[str(protocol_version)]['Clientbound'].items():
			id = int(item[0])
			name = item[1]
			protocol_map_name[id] = name
			protocol_map_id[name] = id

	global original_tmcpr, temp_tmcpr
	original_tmcpr = WorkingDirectory + 'recording.tmcpr'
	temp_tmcpr = WorkingDirectory + 'recording.tmcpr.editing'


def read_int(f):
	data = f.read(4)
	if len(data) < 4:
		return None
	return struct.unpack('>i', data)[0]


def write_int(f, data):
	f.write(struct.pack('>i', data))


def update_tmcpr_on_editing_finished():
	global original_tmcpr, temp_tmcpr
	os.remove(original_tmcpr)
	shutil.move(temp_tmcpr, original_tmcpr)

def save_file():
	print('Saving File')
	with open(WorkingDirectory + 'recording.tmcpr.crc32', 'w') as f:
		f.write(str(utils.crc32_file(WorkingDirectory + 'recording.tmcpr')))
	print('Update recording.tmcpr.crc32 finished')
	global input_file_name
	output_file_name = 'FIX_' + input_file_name
	counter = 2
	while os.path.isfile(output_file_name):
		output_file_name = 'FIX{}_{}'.format(counter, input_file_name)
		counter += 1
	print('Zipping new .mcpr file to {}'.format(output_file_name))
	zipf = zipfile.ZipFile(output_file_name, 'w', zipfile.ZIP_DEFLATED)
	for file in os.listdir(WorkingDirectory):
		zipf.write(WorkingDirectory + file, arcname=file)
	zipf.close()


def set_day_time(day_time):
	global protocol_map_id
	packet = SARCPacket()
	packet.write_varint(protocol_map_id['Time Update'])
	packet.write_long(0)  # World Age
	packet.write_long(-day_time)  # If negative sun will stop moving at the Math.abs of the time
	success = False

	global original_tmcpr, temp_tmcpr
	with open(original_tmcpr, 'rb') as of:
		with open(temp_tmcpr, 'wb') as tf:
			while True:
				time_stamp = read_int(of)
				if time_stamp is None:
					break
				packet_length = read_int(of)
				packet_data = of.read(packet_length)

				if packet_length == 0:
					packet_data = packet.flush()
					success = True

				write_int(tf, time_stamp)
				write_int(tf, packet_length)
				tf.write(packet_data)

	update_tmcpr_on_editing_finished()
	print('Set daytime operation finished, success = {}'.format(success))


def clear_weather():
	global protocol_map_id
	counter = 0
	global original_tmcpr, temp_tmcpr
	with open(original_tmcpr, 'rb') as of:
		with open(temp_tmcpr, 'wb') as tf:
			while True:
				time_stamp = read_int(of)
				if time_stamp is None:
					break
				packet_length = read_int(of)
				packet_data = of.read(packet_length)
				packet = SARCPacket()
				packet.receive(packet_data)
				packet_id = packet.read_varint()

				recorded = True
				if packet_id == protocol_map_id['Change Game State']:
					reason = packet.read_ubyte()
					if reason in [1, 2, 7, 8]:
						recorded = False
				if recorded:
					write_int(tf, time_stamp)
					write_int(tf, packet_length)
					tf.write(packet_data)
				else:
					counter += 1

	update_tmcpr_on_editing_finished()
	print('Clear weather operation finished, deleted {} packets'.format(counter))


def fix_time_stamp():
	global original_tmcpr, temp_tmcpr
	print('Scanning time stamp')
	last_time = None
	a = set()
	with open(original_tmcpr, 'rb') as of:
		while True:
			time_stamp = read_int(of)
			if time_stamp is None:
				break
			packet_length = read_int(of)
			packet_data = of.read(packet_length)
			if last_time is not None:
				a.add(time_stamp - last_time)
			last_time = time_stamp
	last_timestamp_old = last_time
	b = list(a)
	b.sort()
	print('deltas between packets:', b)
	s = input(
		'Input threshold, there should be a big gap near the input value. Input nothing to use default {}\n'.format(
			TriggerAddingDeltaThreshold))
	threshold = int(s) if s != '' else TriggerAddingDeltaThreshold
	print('Fixing time stamp')
	last_time = None
	delta = 0
	with open(original_tmcpr, 'rb') as of:
		with open(temp_tmcpr, 'wb') as tf:
			i = 0
			while True:
				time_stamp = read_int(of)
				if time_stamp is None:
					break
				packet_length = read_int(of)
				packet_data = of.read(packet_length)
				if last_time is not None:
					d = time_stamp - last_time
					if d >= threshold:
						delta += d

				write_int(tf, time_stamp - delta)
				write_int(tf, packet_length)
				tf.write(packet_data)

				last_time = time_stamp
				i += 1
				if i % 100000 == 0:
					print(f'{os.path.getsize(original_tmcpr)}/{os.path.getsize(temp_tmcpr)}')
	last_timestamp_new = last_time

	update_tmcpr_on_editing_finished()
	print('Last time stamp: {} -> {}'.format(last_timestamp_old, last_timestamp_new))
	print('Fixed')


def fix_missing_player():
	print('Fixing missing player (ignore all remove player action in PlayerInfo packet)')

	global original_tmcpr, temp_tmcpr, protocol_map_id
	with open(original_tmcpr, 'rb') as of:
		with open(temp_tmcpr, 'wb') as tf:
			while True:
				time_stamp = read_int(of)
				if time_stamp is None:
					break
				packet_length = read_int(of)
				packet_data = of.read(packet_length)

				packet = SARCPacket()
				packet.receive(packet_data)
				packet_id = packet.read_varint()
				bad = False
				if packet_id == protocol_map_id['Player Info']:
					action = packet.read_varint()
					if action == 4:
						bad = True
				if not bad:
					write_int(tf, time_stamp)
					write_int(tf, packet_length)
					tf.write(packet_data)
	update_tmcpr_on_editing_finished()
	print('Fixed')


def yeet_entity(bad_entity_id):
	global original_tmcpr, temp_tmcpr, protocol_map_id
	print(f'Removing all packets caused by id {bad_entity_id}')
	counter = 0
	blocked_entity_ids = []

	with open(original_tmcpr, 'rb') as of:
		with open(temp_tmcpr, 'wb') as tf:
			num = 0
			while True:
				time_stamp = read_int(of)
				if time_stamp is None:
					break
				packet_length = read_int(of)
				packet_data = of.read(packet_length)

				packet = SARCPacket()
				packet.receive(packet_data)
				packet_id = packet.read_varint()
				packet_name = protocol_map_name[packet_id]

				bad = False
				if packet_name == 'Spawn Mob':
					entity_id = packet.read_varint()
					entity_uuid = packet.read_uuid()
					entity_type = packet.read_byte()
					if entity_type == bad_entity_id:
						blocked_entity_ids.append(entity_id)
						bad = True

				elif packet_name == 'Destroy Entities':
					count = packet.read_varint()
					for i in range(count):
						entity_id = packet.read_varint()
						if entity_id in blocked_entity_ids:
							blocked_entity_ids.remove(entity_id)
						bad = True

				elif packet_name in utils.ENTITY_PACKETS:
					entity_id = packet.read_varint()
					if entity_id in blocked_entity_ids:
						bad = True

				if not bad:
					write_int(tf, time_stamp)
					write_int(tf, packet_length)
					tf.write(packet_data)
				else:
					counter += 1
				num += 1
				if num % 100000 == 0:
					print(f'packet: {num - counter}/{num}, file size: {round(100.0 * os.path.getsize(temp_tmcpr)/os.path.getsize(original_tmcpr), 2)}%')
	update_tmcpr_on_editing_finished()
	print('Removed {} packets'.format(counter))


def yeet_all_entity_except_player():
	global original_tmcpr, temp_tmcpr, protocol_map_id
	print(f'Removing all non-player entity packets')
	counter = 0
	player_ids = []

	with open(original_tmcpr, 'rb') as of:
		with open(temp_tmcpr, 'wb') as tf:
			num = 0
			processed = 0
			while True:
				time_stamp = read_int(of)
				if time_stamp is None:
					break
				packet_length = read_int(of)
				packet_data = of.read(packet_length)

				packet = SARCPacket()
				packet.receive(packet_data)
				packet_id = packet.read_varint()
				packet_name = protocol_map_name[packet_id]

				bad = False

				if packet_name == 'Spawn Player':
					entity_id = packet.read_varint()
					uuid = packet.read_uuid()
					if entity_id not in player_ids:
						player_ids.append(entity_id)

				if packet_name == 'Spawn Mob':
					bad = True

				elif packet_name == 'Destroy Entities':
					count = packet.read_varint()
					has_player = False
					for i in range(count):
						entity_id = packet.read_varint()
						if entity_id in player_ids:
							player_ids.remove(entity_id)
							has_player = True
					if not has_player:
						bad = True

				elif packet_name in utils.ENTITY_PACKETS:
					entity_id = packet.read_varint()
					if entity_id not in player_ids:
						bad = True

				if not bad:
					write_int(tf, time_stamp)
					write_int(tf, packet_length)
					tf.write(packet_data)
				else:
					counter += 1
				num += 1
				processed += 8 + packet_length
				if num % 100000 == 0:
					print(f'packet: {num - counter}/{num}, file size: {round(100.0 * processed/os.path.getsize(original_tmcpr), 2)}%')
	update_tmcpr_on_editing_finished()
	print('Removed {} packets'.format(counter))


def yeet_packet(bad_packet_name):
	global original_tmcpr, temp_tmcpr, protocol_map_id
	print(f'Removing all packet named {bad_packet_name}')
	counter = 0

	with open(original_tmcpr, 'rb') as of:
		with open(temp_tmcpr, 'wb') as tf:
			num = 0
			processed = 0
			while True:
				time_stamp = read_int(of)
				if time_stamp is None:
					break
				packet_length = read_int(of)
				packet_data = of.read(packet_length)

				packet = SARCPacket()
				packet.receive(packet_data)
				packet_id = packet.read_varint()
				packet_name = protocol_map_name[packet_id]

				if packet_name != bad_packet_name:
					write_int(tf, time_stamp)
					write_int(tf, packet_length)
					tf.write(packet_data)
				else:
					counter += 1
				num += 1
				processed += 8 + packet_length
				if num % 100000 == 0:
					print(f'packet: {num - counter}/{num}, file size: {round(100.0 * processed/os.path.getsize(original_tmcpr), 2)}%')
	update_tmcpr_on_editing_finished()
	print('Removed {} packets'.format(counter))


def analyze():
	print('What'' type of packet takes the most space')
	counter = {}
	global original_tmcpr, protocol_map_id, protocol_map_name
	entity_type_map = {}
	player_ids = []
	with open(original_tmcpr, 'rb') as of:
		all = 0
		num = 0
		while True:
			time_stamp = read_int(of)
			if time_stamp is None:
				break
			packet_length = read_int(of)
			packet_data = of.read(packet_length)
			packet = SARCPacket()
			packet.receive(packet_data)
			packet_id = packet.read_varint()
			packet_name = protocol_map_name[packet_id]
			entity_type = None

			if packet_name == 'Spawn Player':
				entity_id = packet.read_varint()
				uuid = packet.read_uuid()
				if entity_id not in player_ids:
					player_ids.append(entity_id)
			elif packet_name == 'Spawn Mob' or packet_name == 'Spawn Object':
				entity_id = packet.read_varint()
				entity_uuid = packet.read_uuid()
				entity_type = packet.read_byte()
				entity_type_map[entity_id] = ('Mob' if packet_name == 'Spawn Mob' else 'Obj') + str(entity_type)
				entity_type = entity_type_map[entity_id]
			elif packet_name == 'Destroy Entities':
				count = packet.read_varint()
				for i in range(count):
					entity_id = packet.read_varint()
					if entity_id in player_ids:
						player_ids.remove(entity_id)

			elif packet_name in utils.ENTITY_PACKETS:
				entity_id = packet.read_varint()
				entity_type = entity_type_map.get(entity_id, '?')
				if entity_id in player_ids:
					entity_type = 'Player'

			if entity_type is not None:
				packet_name += ' (' + entity_type + ')'

			if packet_name not in counter:
				counter[packet_name] = 0
			counter[packet_name] += 8 + packet_length
			all += 8 + packet_length
			num += 1
			if num % 100000 == 0:
				print(f'scanned: {round(100.0 * all/os.path.getsize(original_tmcpr), 2)}%')

	arr = list(counter.items())
	arr.sort(key=lambda x: x[1], reverse=True)
	for a in arr:
		print(f'{a[0]}: {round(a[1] / utils.BytePerMB, 5)}MB')

	print('Done')

print('A script to fix some bugs in recording file recorded by PCRC in old versions')
print('It can be optimize a lot but I\'m too lazy xd. Whatever it works, but it may consume a lots of RAM')
print('Only works for 1.14.4 recording file')

prepare()
print('Init finish')

CommandListMessageData = collections.namedtuple('CommandListMessageData', ['id', 'name', 'detail'])
CommandList = [
	CommandListMessageData(0, 'Save and Exit', 'Exit the tool'),
	CommandListMessageData(1, 'Time and weather fix',
						   'Fix missing time update packet and delete remaining weather packet in PCRC 0.3-alpha and below'),
	CommandListMessageData(2, 'Wrong packet time stamp fix after afk',
						   'Fix wrong time stamp (missing afktime) in a packet in PCRC 0.5-alpha and below'),
	CommandListMessageData(3, 'Player missing fix after afk',
						   'Fix player not gets rendered after PCRC afk in PCRC 0.5-alpha and below. It\'s a bit hacky'),
	CommandListMessageData(4, 'Analyze recording file size', ''),
	CommandListMessageData(5, 'Yeet all zombie pigman related packets', ''),
	CommandListMessageData(6, 'Yeet all non-player entity packets', ''),
	CommandListMessageData(7, 'Yeet all packets with specific type', ''),
]
CommandListMessage = 'Command List:\n' + '\n'.join(['{}. {}'.format(cmd.id, cmd.name) for cmd in CommandList])
while True:
	print()
	print(CommandListMessage)
	cmd = input('> ')
	try:
		msg = CommandList[int(cmd)].detail
	except:
		pass
	else:
		print('Command effect:', msg)
	if cmd == '0':
		save_file()
		shutil.rmtree(WorkingDirectory)
		break
	elif cmd == '1':
		do_set_daytime = input('Set daytime? (0: no; 1: yes) = ') == '1'
		if do_set_daytime:
			day_time = int(input('Daytime = '))
		do_clear_weather = input('Clear weather? (0: no; 1: yes) = ') == '1'
		if do_set_daytime:
			set_day_time(day_time)
		if do_clear_weather:
			clear_weather()
	elif cmd == '2':
		fix_time_stamp()
	elif cmd == '3':
		fix_missing_player()
	elif cmd == '4':
		analyze()
	elif cmd == '5':
		yeet_entity(56) # PigZombie / minecraft:zombie_pigman
	elif cmd == '6':
		yeet_all_entity_except_player()
	elif cmd == '7':
		packet_name = input('Input packet name, u can find the name in https://wiki.vg/\nname = ')
		yeet_packet(packet_name)
	else:
		print('Unknown command')
input('press enter to exit')
