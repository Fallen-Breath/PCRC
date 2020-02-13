# coding: utf8
import gc
import json
import os
import shutil
import struct
import sys
import zipfile
import collections

try:
	from SARC.packet import Packet as SARCPacket
except ImportError: # in tools/ folder
	sys.path.append("../")
	from SARC.packet import Packet as SARCPacket
import utils

class Data:
	def __init__(self, time_stamp, packet_length, packet):
		self.time_stamp = time_stamp
		self.packet_length = packet_length
		self.packet = packet

datas = []
WorkingDirectory = '__RFETMP__/'
TriggerAddingDeltaThreshold = 10000
PlayerInfoId = 0x33
TimeUpdatePacketId = 78
ChangeGameStateId = 30

def read_int(f):
	data = f.read(4)
	if len(data) < 4:
		return None
	return struct.unpack('>i', data)[0]

def write_int(f, data):
	f.write(struct.pack('>i', data))

def read_tmcpr(file_name):
	global datas
	datas = []
	with open(file_name, 'rb') as f:
		while True:
			time_stamp = read_int(f)
			if time_stamp is None:
				break
			packet_length = read_int(f)
			datas.append(Data(time_stamp, packet_length, f.read(packet_length)))
	print('Packet count =', len(datas))

def save_file():
	print('Saving File')
	global datas
	with open(WorkingDirectory + 'recording.tmcpr', 'wb') as f:
		for data in datas:
			write_int(f, data.time_stamp)
			write_int(f, data.packet_length)
			f.write(data.packet)
	print('Update recording.mcpr finished')
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
	global datas
	packet = SARCPacket()
	packet.write_varint(TimeUpdatePacketId)
	packet.write_long(0)
	packet.write_long(-day_time)  # If negative sun will stop moving at the Math.abs of the time
	bytes = packet.flush()
	time_data = Data(0, len(bytes), bytes)
	success = False
	for i in range(len(datas)):
		if datas[i].packet_length == 0:
			datas[i] = time_data
			success = True
			break
	print('Set daytime operation finished, success = {}'.format(success))

def clear_weather():
	global datas
	counter = 0
	new_datas = []
	for i in range(len(datas)):
		recorded = True
		packet = SARCPacket()
		packet.receive(datas[i].packet)
		packet_id = packet.read_varint()
		if packet_id == ChangeGameStateId:
			reason = packet.read_ubyte()
			if reason in [1, 2, 7, 8]:
				recorded = False
		if recorded:
			new_datas.append(datas[i])
		else:
			counter += 1
	del datas
	gc.collect()
	datas = new_datas
	print('Clear weather operation finished, deleted {} packets'.format(counter))

def fix_time_stamp():
	print('Scanning time stamp')
	global datas
	last_time = None
	a = set()
	for data in datas:
		if last_time is not None:
			a.add(data.time_stamp - last_time)
		last_time = data.time_stamp
	b = list(a)
	b.sort()
	print('deltas between packets:', b)
	s = input('Input threshold, there should be a big gap near the input value. Input nothing to use default {}\n'.format(TriggerAddingDeltaThreshold))
	threshold = int(s) if s != '' else TriggerAddingDeltaThreshold
	print('Fixing time stamp')
	last_time = None
	delta = 0
	new_datas = []
	for i in range(len(datas)):
		if last_time is not None:
			d = datas[i].time_stamp - last_time
			if d >= threshold:
				delta += d
		new_datas.append(Data(datas[i].time_stamp - delta, datas[i].packet_length, datas[i].packet))
		last_time = datas[i].time_stamp
		if i % 100000 == 0:
			print(f'{i}/{len(datas)}')
	print('Last time stamp: {} -> {}'.format(datas[-1].time_stamp, new_datas[-1].time_stamp))
	datas = new_datas
	print('Fixed')


def fix_missing_player():
	global datas
	print('Fixing missing player (ignore all remove player action in PlayerInfo packet)')
	new_datas = []
	for data in datas:
		packet = SARCPacket()
		packet.receive(data.packet)
		packet_id = packet.read_varint()
		bad = False
		if packet_id == PlayerInfoId:
			action = packet.read_varint()
			if action == 4:
				bad = True
		if not bad:
			new_datas.append(data)
	datas = new_datas
	print('Fixed')



print('A script to fix some bugs in recording file recorded by PCRC in old versions')
print('It can be optimize a lot but I\'m too lazy xd. Whatever it works, but it may consume a lots of RAM')
print('Only works for 1.14.4 recording file')
with open('..\protocol.json', 'r') as f:
	protocolMap = json.load(f)[str(498)]['Clientbound']
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
print('Reading')
read_tmcpr(WorkingDirectory + 'recording.tmcpr')
print('Init finish')

CommandListMessageData = collections.namedtuple('CommandListMessageData', ['id', 'name', 'detail'])
CommandList = [
	CommandListMessageData(0, 'Save and Exit', 'Exit the tool'),
	CommandListMessageData(1, 'Time and weather fix', 'fix missing time update packet and delete remaining weather packet in PCRC 0.3-alpha and below'),
	CommandListMessageData(2, 'Wrong packet time stamp fix after afk', 'Fix wrong time stamp (missing afktime) in a packet in PCRC 0.5-alpha and below'),
	CommandListMessageData(3, 'Player missing fix after afk', 'Fix player not gets rendered after PCRC afk in PCRC 0.5-alpha and below. It\'s a bit hacky'),
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
	else:
		print('Unknown command')
input('press enter to exit')
