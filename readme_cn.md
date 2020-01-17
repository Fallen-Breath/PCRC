PCRC
--------

[English](https://github.com/Fallen-Breath/PCRC/blob/master/readme.md)

> 基于 PyCraft 的 Replay 客户端

~~SARC在 1.13 后跑不起来了，所以我搓了个这个东西~~

这是一个 Minecraft 客户端，它可以录制出能被 [Replay Mod](https://www.replaymod.com/) 识别的录像文件（*.mcpr）

非常感谢 [SARC](https://github.com/Robitobi01/SARC) 提供了 replay 相关的逻辑处理部分与 [pyCraft](https://github.com/ammaraskar/pyCraft) 提供了 Minecraft 客户端相关的东西

**仅支持 1.14.4 的服务器**，虽然只要改一改，就能让它支持任何 pyCraft 支持的版本

## 环境要求

Python 的版本需要 python3，至少它在 Python 3.6 与 Python 3.8 中能运行

### Python 模块

- cryptography
- requests
- future
- PyYAML

所需的模块也已储存在 `requirements.txt`中

## 优势

- 可以在托管在服务端上 24/7 录制
- 可以设置为仅在玩家在附近时进行录制
- 有多个选项可以设置以满足多种录制需求


## 配置文件

配置文件为 `config.json`

`language` : PCRC 机器人使用的语言。语言文件需放置于 `lang/`

`online_mode` : 是否使用正版登录

`username` : 用于盗版登录的玩家id，或者是用于正版登录的 Minecraft 账号的邮箱

`password` : 用于正版登录时的 Minecraft 账号的密码

`address` : Minecraft 服务器的 IP 地址

`port` : Minecraft 服务器的端口

`minimal_packets` : 在这个选项设为 `true` 时 PCRC会仅录制能能维持录制的最小数量的数据包。 可用于在录制超长时间延迟摄影时减小文件大小

`daytime` : 将游戏时间设置为一个固定值并忽略之后所有的时间变化。将其设为 `-1` 以录制正常的昼夜循环

`weather` : 是否录制天气

`with_player_only` : 是否只当玩家在附近时才进行录制

`remove_items` : 是否忽略掉落物

`remove_bats` : 是否忽略蝙蝠

`upload_file` : 是否将录制好的文件上传至 [transfer.sh](transfer.sh) 以便进行分享~~（国内用户还是关掉吧不然上传十年）~~

`auto_relogin` : 当客户端掉线时是否自动重连。若为 `true`，PCRC 会在掉线 3 秒后尝试重连

`debug_mode` : 输出调试信息用

## 指令

### 控制台指令

`start`: 开启PCRC 并开始录制

`stop`: 停止 PCRC 并关闭录制

`restart`: 重启 PCRC

`exit`: 退出程序

`say <信息>`: 将文字 `<信息>` 作为聊天信息发送至服务器

`set <选项> <值>` 将 PCRC 与配置文件中的 <选项> 设置为 <值>

### 游戏内指令

使用游戏内的聊天来触发命令

`!!PCRC`: 显示帮助信息	

`!!PCRC status`: 显示状态

`!!PCRC here`: 发送一个“!!here”指令

`!!PCRC pos`: 显示所处位置，不一定 100% 准确

`!!PCRC sepc`: 旁观者传送至发送指令的玩家

`!!PCRC stop`: 关闭 PCRC

`!!PCRC restart`: 重启 PCRC

`!!PCRC url`: 输出所有已录制文件的网址

`!!PCRC set`: 输出所有可设置的选项

`!!PCRC set` <选项> <值>: 将<选项>设置为<值>，不会写入配置文件