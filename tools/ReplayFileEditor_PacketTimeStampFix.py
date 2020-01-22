# coding: utf8

import os
import shutil
import struct
import sys
import zipfile

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
	s = input('Input threshold, input nothing to use default {}\n'.format(TriggerAddingDeltaThreshold))
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

	for i in range(1, len(datas)):
		if datas[i].time_stamp - datas[i - 1].time_stamp < 0:
			print('wtf at', i)

def save_file():
	global datas
	with open(WorkingDirectory + 'recording.tmcpr', 'wb') as f:
		for data in datas:
			write_int(f, data.time_stamp)
			write_int(f, data.packet_length)
			f.write(data.packet)
	print('Update recording.mcpr finished')
	with open(WorkingDirectory + 'recording.tmcpr.crc32', 'w') as f:
		f.write(str(utils.crc32f(WorkingDirectory + 'recording.tmcpr')))
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
	shutil.rmtree(WorkingDirectory)



print('A script to fix wrong time stamp (missing afktime) in a packet in whatever alpha version')
print('It can be optimize a lot but I\'m too lazy xd. whatever it works')
input_file_name = None
if len(sys.argv) >= 2:
	input_file_name = sys.argv[1]
while True:
	if input_file_name is None:
		input_file_name = input('Input .mcpr file name: ')
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
fix_time_stamp()
print('Operation finished, saving file')
save_file()
input('Finish! press enter to exit')
