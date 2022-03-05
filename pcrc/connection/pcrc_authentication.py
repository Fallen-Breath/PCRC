import json
from typing import Tuple
from uuid import uuid4

import requests

from minecraft.authentication import AuthenticationToken


class AuthenticateException(Exception):
	pass


class PcrcAuthenticationToken(AuthenticationToken):
	MS_AUTH_URL = 'https://login.live.com/oauth20_authorize.srf?client_id=00000000402b5328&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf'

	def microsoft_authenticate(self, auth_code: str):
		mc_token, uuid, player_name = MicrosoftAuthenticator(auth_code).authenticate()
		self.username = player_name
		self.access_token = mc_token
		self.client_token = uuid4().hex
		self.profile.id_ = uuid
		self.profile.name = player_name
		return True

	def mojang_authenticate(self, username: str, password: str):
		self.authenticate(username, password)


class MicrosoftAuthenticator:
	"""
	Reference: https://wiki.vg/Microsoft_Authentication_Scheme
	"""
	__JSON_TYPE_HEADER = {
		'Content-Type': 'application/json',
		'Accept': 'application/json'
	}

	def __init__(self, auth_code: str):
		self.auth_code: str = auth_code

	def authenticate(self) -> Tuple[str, str, str]:
		"""
		:return: mc_token, uuid, player_name
		"""
		access_token = self._get_access_token(self.auth_code)
		xbl_token = self._authenticate_xbl(access_token)
		xsts_token, user_hash = self._authenticate_xsts(xbl_token)
		mc_token = self._authenticate_minecraft(xsts_token, user_hash)
		uuid, player_name = self._get_uuid(mc_token)
		return mc_token, uuid, player_name

	@classmethod
	def _get_access_token(cls, access_code: str):
		context = {
			'client_id': '00000000402b5328',
			'code': access_code,
			'grant_type': 'authorization_code',
			'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
			'scope': 'service::user.auth.xboxlive.com::MBI_SSL'
		}
		response = requests.post('https://login.live.com/oauth20_token.srf', context)
		return response.json()['access_token']

	@classmethod
	def _authenticate_xbl(cls, access_token: str) -> str:
		"""
		:return: xbl token, user hash
		"""
		context = {
			'Properties': {
				"AuthMethod": "RPS",
				'SiteName': 'user.auth.xboxlive.com',
				'RpsTicket': access_token
			},
			'RelyingParty': "http://auth.xboxlive.com",
			'TokenType': 'JWT'
		}
		response = requests.post('https://user.auth.xboxlive.com/user/authenticate', json.dumps(context), headers=cls.__JSON_TYPE_HEADER)
		if response.content == b'':
			raise AuthenticateException('Microsoft access token expired')
		else:
			return response.json()['Token']

	@classmethod
	def _authenticate_xsts(cls, xbl_token: str) -> Tuple[str, str]:
		"""
		:return: xsts token, user hash
		"""
		context = {
			'Properties': {
				'SandboxId': 'RETAIL',
				'UserTokens': [
					xbl_token
				]
			},
			'RelyingParty': 'rp://api.minecraftservices.com/',
			'TokenType': 'JWT'
		}
		response = requests.post('https://xsts.auth.xboxlive.com/xsts/authorize', json.dumps(context), headers=cls.__JSON_TYPE_HEADER)
		data = response.json()
		return data['Token'], data['DisplayClaims']['xui'][0]['uhs']

	@classmethod
	def _authenticate_minecraft(cls, xsts_token: str, user_hash: str):
		context = {
			'identityToken': 'XBL3.0 x={};{}'.format(user_hash, xsts_token)
		}
		response = requests.post("https://api.minecraftservices.com/authentication/login_with_xbox", json.dumps(context), headers=cls.__JSON_TYPE_HEADER)
		return response.json()['access_token']

	@classmethod
	def _get_uuid(cls, mc_token: str) -> Tuple[str, str]:
		headers = dict(Authorization="Bearer {}".format(mc_token))
		res = requests.get("https://api.minecraftservices.com/minecraft/profile", headers=headers)
		data = res.json()
		return data['id'], data['name']
