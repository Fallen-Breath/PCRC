import requests
import json
from ..logger import Logger

logger = Logger(name='PCRC')

# https://login.live.com/oauth20_authorize.srf?client_id=00000000402b5328&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf
def getTokenByAccessCode(i):
    context = {"client_id": "00000000402b5328",
               "code": i,
               "grant_type": "authorization_code",
               "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
               "scope": "service::user.auth.xboxlive.com::MBI_SSL"}

    response = requests.post("https://login.live.com/oauth20_token.srf", context)
    return response.json().get("access_token")


def XBL(i):
    headers = {'Content-Type': 'application/json', "Accept": "application/json"}
    context = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": i
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }
    response = requests.post("https://user.auth.xboxlive.com/user/authenticate", json.dumps(context), headers=headers)
    if response.content == b'':
        msg = "microsoft token is expired! Get it from https://login.live.com/oauth20_authorize.srf?client_id=00000000402b5328&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf"
        raise ValueError(msg)
    else:
        return response.json().get("Token")


def XSL(i):
    headers = {'Content-Type': 'application/json', "Accept": "application/json"}
    context = {
        "Properties": {
            "SandboxId": "RETAIL",
            "UserTokens": [
                i
            ]
        },
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }
    response = requests.post("https://xsts.auth.xboxlive.com/xsts/authorize", json.dumps(context), headers=headers)
    response = response.json()
    return response.get("Token"), response.get("DisplayClaims").get("xui")[0].get("uhs")


def minecraft(token, uhs):
    headers = {'Content-Type': 'application/json', "Accept": "application/json"}
    context = {
        "identityToken": f"XBL3.0 x={uhs};{token}"
    }
    response = requests.post("https://api.minecraftservices.com/authentication/login_with_xbox", json.dumps(context), headers=headers)

    return response.json().get("access_token")


def getUuid(i):
    headers = {"Authorization": f"Bearer {i}"}
    res = requests.get("https://api.minecraftservices.com/minecraft/profile", headers=headers)
    res = res.json()
    return res.get("id"), res.get("name")


def get_login_info(accessCode: str) -> list:
    Token = getTokenByAccessCode(accessCode)
    XBL_token = XBL(Token)
    XSL_token, uhs = XSL(XBL_token)
    MineToken = minecraft(XSL_token, uhs)
    ID, Name = getUuid(MineToken)
    return [MineToken, ID, Name]
