import os
import time
import json
import select
import requests
import urllib.request
from _sha1 import sha1
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_der_public_key
from connection import *
from packet import *


# Script to automatically generate name to packet_id tables based on data from wiki.vg
# Currrently avaliable protocol versions:
#  340, 338, 335, 316, 315, 210, 110, 109, 107, 47, 5, 4

# Shortens decode with error avoidance
def decode(s, encoding='utf-8', errors='ignore'):
    return s.decode(encoding=encoding, errors=errors)


# Gets a list of links to the version appropitate article
def gen_version_links():
    page = urllib.request.urlopen('http://wiki.vg/Protocol_version_numbers')
    html = page.read().decode('utf-8', errors='ignore').splitlines()
    version_links = {}
    for line in html:
        if 'Retrieved from' in line:
            break
        if 'title=Protocol' in line and int(
                line.split('oldid=')[1].split('">page')[0]) > 5000:  # and 'Pre-release_protocol' not in line:
            link = line.replace('amp;', '').split('href="')[1].split('">page')[0]
            version = int(html[html.index(line) - 2].split('> ')[1])
            version_links[version] = link
    return version_links


# Gets the list of play state server & clientbound packets for the given version
def gen_version_protocol(version):
    version_links = gen_version_links()
    if version not in version_links:
        raise IOError('Protocol version doesnt get supported')
    link = version_links[version]
    page = urllib.request.urlopen(link)
    html = page.read().decode('utf-8', errors='ignore').splitlines()
    counter = []
    temp = {}
    packets = {'Clientbound': {}, 'Serverbound': {}}
    for line in html:  # Gets a list of all the index entries(e.g. 4.1.1 Keep Alive)
        if '<li class="toclevel-' in line:
            number = line.split('class="tocnumber">')[1].split('</span>')[0]
            if number.count('.') == 2:
                name = line.split('class="toctext">')[1].split('</span>')[0]
                counter.append(number[:1])
                temp[number] = name
    counter = {x: counter.count(x) for x in counter}  # Counts amount of first index numbers(e.g. 4 <-- .1.1 Keep Alive)
    for key in temp:  # Gets play state from first index number by taking most common one
        if key[:1] == max(counter, key=counter.get):
            packet_id = int(key[4:].split(':')[
                                0]) - 1  # Generates packet_id by -1 from the last index number(e.g. 4.1. --> 1 - 1 = 0x0)
            if int(key[2:3]) == 1:
                packets['Clientbound'][str(packet_id)] = temp[key]
            else:
                packets['Serverbound'][
                    temp[key]] = packet_id  # Is client or server side by the middle index number(e.g. 4. --> 1.1)
    return {str(version): packets}


# Makes request to the Mojang authentication server(Yggdrasil)
def authenticate(username, password):
    response = requests.post('https://authserver.mojang.com/authenticate',
                             data=json.dumps({'username': username, 'password': password,
                                              'agent': {'name': 'Minecraft', 'version': 1}}),
                             headers={'content-type': 'application/json'})
    return response.json()


# Requests authentication and returns a dict of the needed information
def generate_dict(hash, email, password):
    data = dict()
    response = authenticate(email, password)
    print(response)
    access_token = response['accessToken']
    uuid = response['selectedProfile']['id']
    user_name = response['selectedProfile']['name']
    data[hash] = {'access_token': access_token, 'uuid': uuid, 'user_name': user_name, 'uses': 1,
                  'created': int(time.time())}
    return data




# Test if given packet hould be ignored
def is_bad_packet(packet_name, minimal_packets=False):
    if packet_name in BAD_PACKETS:
        return True
    if minimal_packets and packet_name in USELESS_PACKETS:
        return True
    return False


# Reading config
def load_config():
    with open('config.json', 'r') as json_file:
        config = json.load(json_file)
        email = config['username']
        password = config['password']
    return config, email, password


# Check if valid token exists, else make a new one
def get_token(email, password):
    # Access token caching.
    hash = sha1()
    hash.update(str.encode(email))
    hash = hash.hexdigest()
    if not os.path.exists('accessToken.json'):  # Create file if not existing
        with open('accessToken.json', 'w'): pass

    with open('accessToken.json', 'r') as file:
        try:
            json_data = json.load(file)
        except json.decoder.JSONDecodeError:  # File is new and no json avaliable
            json_data = ''
    # Hashed email doesnt exist --> account not cached --> refresh
    # Token used more than 10 times --> refresh
    # Token older than 10 minutes --> refresh
    if hash not in json_data or \
            json_data[hash]['uses'] > 10 or \
            int(time.time()) - json_data[hash]['created'] > 600:
        print('New token generated')
        json_data = generate_dict(hash, email, password)
        with open('accessToken.json', 'w') as json_file:
            json.dump(json_data, json_file)

    # If email has cached token
    if hash in json_data:
        print('Stored token used')
        json_data[hash]['uses'] += 1
        with open('accessToken.json', 'w') as json_file:
            json.dump(json_data, json_file)

    access_token = json_data[hash]['access_token']
    uuid = json_data[hash]['uuid']
    user_name = json_data[hash]['user_name']
    return access_token, uuid, user_name


# Serverping to get protocol version and create table
def generate_protocol_table(address):
    # Handshake with Next state set to 1 (status) to receive protocol version
    protocol_connection = TCPConnection(address)
    packet_out = Packet()
    packet_out.write_varint(0x00)
    packet_out.write_varint(335)
    packet_out.write_utf(address[0])
    packet_out.write_ushort(address[1])
    packet_out.write_varint(1)
    protocol_connection.send_packet(packet_out)
    packet_out = Packet()
    packet_out.write_varint(0x00)
    protocol_connection.send_packet(packet_out)
    while True:
        ready_to_read = select.select([protocol_connection.socket], [], [], 0)[0]
        if ready_to_read:
            packet_in = protocol_connection.receive_packet()
            packet_id = packet_in.read_varint()
            protocol_connection.socket.close()
            status_data = json.loads(packet_in.read_utf())
            protocol_version = status_data['version']['protocol']
            mc_version = status_data['version']['name']
            break
    print(status_data)
    # Generating needed protocol version table
    try:
        with open('protocol.json', 'r') as json_file:
            json_data = json.load(json_file)
    except:
        json_data = ''
    if json_data == '' or str(protocol_version) not in json_data:
        with open('protocol.json', 'w') as json_file:
            packets = gen_version_protocol(protocol_version)
            json.dump(packets, json_file, indent=4)
            print('Protocol generated')
            json_data = packets
    else:
        print('Protocol avaliable')
    clientbound = json_data[str(protocol_version)]['Clientbound']
    serverbound = json_data[str(protocol_version)]['Serverbound']
    return clientbound, serverbound, protocol_version, mc_version


# Login and encryption + compression
def login(address, protocol_version, debug, access_token, uuid, user_name):
    connection = TCPConnection(address, debug)

    # Handshake with Next state set to 2 (login)
    packet_out = Packet()
    packet_out.write_varint(0x00)
    packet_out.write_varint(protocol_version)
    packet_out.write_utf(address[0])
    packet_out.write_ushort(address[1])
    packet_out.write_varint(2)
    connection.send_packet(packet_out)

    # Login start
    packet_out = Packet()
    packet_out.write_varint(0x00)
    packet_out.write_utf(user_name)
    connection.send_packet(packet_out)

    # Begin login phase loop.
    while True:
        receive_ready, send_ready, exception_ready = select.select([connection.socket], [connection.socket], [], 0.01)
        if len(receive_ready) > 0:
            packet_in = connection.receive_packet()
            packet_id = packet_in.read_varint()
            if debug:
                print('L Packet ' + hex(packet_id))

            # Disconnect (login)
            if packet_id == 0x00:
                print(packet_in.read_utf())

            # Encryption request
            if packet_id == 0x01:
                server_id = packet_in.read_utf()
                pub_key = packet_in.read_bytearray_as_str()
                ver_tok = packet_in.read_bytearray_as_str()

                # Client auth
                shared_secret = os.urandom(16)
                verify_hash = sha1()
                verify_hash.update(server_id.encode('utf-8'))
                verify_hash.update(shared_secret)
                verify_hash.update(pub_key)
                server_id = format(int.from_bytes(verify_hash.digest(), byteorder='big', signed=True), 'x')
                res = requests.post('https://sessionserver.mojang.com/session/minecraft/join',
                                    data=json.dumps({'accessToken': access_token, 'selectedProfile': uuid,
                                                     'serverId': server_id}),
                                    headers={'content-type': 'application/json'})
                print('Client session auth', res.status_code)

                # Send Encryption Response
                packet_out = Packet()
                packet_out.write_varint(0x01)
                pub_key = load_der_public_key(pub_key, default_backend())
                encrypt_token = pub_key.encrypt(ver_tok, PKCS1v15())
                encrypt_secret = pub_key.encrypt(shared_secret, PKCS1v15())
                packet_out.write_varint(len(encrypt_secret))
                packet_out.write(encrypt_secret)
                packet_out.write_varint(len(encrypt_token))
                packet_out.write(encrypt_token)
                connection.send_packet(packet_out)
                connection.configure_encryption(shared_secret)

            # Login Success
            if packet_id == 0x02:
                u = packet_in.read_utf()
                n = packet_in.read_utf()
                print('Name: ' + n + '  |  UUID: ' + u)
                print('Switching to PLAY')
                break

            # Set Compression
            if packet_id == 0x03:
                connection.compression_threshold = packet_in.read_varint()
                print('Compression enabled, threshold:', connection.compression_threshold)
    return connection


# Send a tabcomplete to get full list of operators
def request_ops(connection, serverbound):
    packet_out = Packet()
    packet_out.write_varint(serverbound['Tab-Complete (serverbound)'])
    packet_out.write_utf('/deop ')
    packet_out.write_bool(True)
    packet_out.write_bool(False)
    connection.send_packet(packet_out)


# Send a chatmessage
def send_chat_message(connection, serverbound, message):
    packet_out = Packet()
    packet_out.write_varint(serverbound['Chat Message (serverbound)'])
    packet_out.write_utf(message)
    connection.send_packet(packet_out)


# Returns a string like h:m for given millis
def convert_millis(millis):
    seconds = int(millis / 1000) % 60
    minutes = int(millis / (1000 * 60)) % 60
    hours = int(millis / (1000 * 60 * 60))
    if seconds < 10:
        seconds = '0' + str(seconds)
    if minutes < 10:
        minutes = '0' + str(minutes)
    if hours < 10:
        hours = '0' + str(hours)
    return str(hours) + ':' + str(minutes) + ':' + str(seconds)
