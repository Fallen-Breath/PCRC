import os
import time
import json
import select
import requests
import urllib.request
from _sha1 import sha1
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_der_public_key
from .packet import *


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
def gen_version_protocol_from_link(version, link):
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

