PCRC
--------

[中文](https://github.com/Fallen-Breath/PCRC/blob/master/readme_cn.md)

> PyCraft based Replay Client

~~SARC doesn't work in 1.13+ version so I made this crap~~

An Minecraft client that can record a replay file (*.mcpr) which can be recognized by [Replay Mod](https://www.replaymod.com/)

Great thanks to [SARC](https://github.com/Robitobi01/SARC) for the replay logic stuffs and [pyCraft](https://github.com/ammaraskar/pyCraft) for the minecraft client stuffs

**Supports 1.14.4 server only** tho with a bit modification it works in any version as long as pyCraft supports that

## Environment

Python version should be python3 and at least it works on Python 3.6 and Python 3.8

### Python modules

- cryptography
- requests
- future
- PyYAML

The requirements are also stored in `requirements.txt`

## Advantage

- Can be hosted server side for 24/7 recording
- It can be set to record only when the player is nearby
- Multiple options can be set for custom recording
- Restart after raw file size reaches 512MB or recording time reaches 5 hours to prevent oversize recording

## Config

The config file is `config.json`

`language`: The language that the PCRC bot will speak in the game. Language file should be in folder `lang/`

`online_mode`: Use online mode to login or offline mode instead

`username`: Username for offline mode or email for the used Minecraft account

`password`: Password for the used Minecraft account if login in in online mode

`address`: IP Address of the Minecraft server

`port`: Port of the Minecraft server

`minimal_packets`: PCRC will only record the minimum needed packets for a proper recording when this option is turned on. This should be used to decrease the filesize of recordings while recording long term projects (timelapse)

`daytime`: Sets the daytime once to the defined time in the recording and ignores all further changes from the server. If set to `-1` the normal day/night cycle is recorded

`weather`: Turns weather in the recording on or off

`with_player_only`: If set to true, PCRC only record packets if there are players nearby

`remove_items`: If set to true, all dropped items wont be recorded. This can potentially decrease filesize

`remove_bats`: If set to true, bats wont be recorded. This can potentially decrease filesize

`upload_file`: If set to true, .mcpr file will be sent to [transfer.sh](transfer.sh) after finishing recording

`auto_relogin`: If this option is enabled and the client gets disconnected, it will automatically try to reconnect

`debug_mode`: Outputs debug info

## Command

### Console Command

`start`: start PCRC and start recording

`stop`: stop PCRC and stop recording

`restart`: restart PCRC

`exit`: exit the program

`say <text>`: send text `<text>` to the server as a chat message

`set <option> <value>` set option to value of PCRC and in the config file

### In Game Command

Using normal in game chatting to trigger

`!!PCRC`: show help

`!!PCRC status`: show status

`!!PCRC here`: emit a "!!here" command

`!!PCRC pos`: show position, might not be 100% accurate

`!!PCRC spec`: spectator teleport to the player

`!!PCRC stop`: stop PCRC

`!!PCRC restart`: restart PCRC

`!!PCRC url`: print all urls of recorded files

`!!PCRC set`: print all settable option

`!!PCRC set <option> <value>`: set the value of `<option>` to `<value>` which won't write to config file

`!!PCRC name <filename>`: set recording file name to `<filename>`
