import json
from logging import Logger
from typing import Tuple, Optional
from uuid import uuid4

import requests

from minecraft.authentication import AuthenticationToken


class AuthenticateException(Exception):
	pass


class AuthType:
	offline = 'offline'
	mojang = 'mojang'
	microsoft = 'microsoft'


class PcrcAuthenticationToken(AuthenticationToken):
	MS_AUTH_URL = 'https://login.live.com/oauth20_authorize.srf?client_id=00000000402b5328&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf'

	def __init__(self, logger: Logger):
		super().__init__()
		self.logger = logger
		self.__mc_auth = MicrosoftAuthenticator(self.logger)

	def microsoft_authenticate(self, auth_code: str):
		mc_token, uuid, player_name = self.__mc_auth.authenticate(auth_code)
		self.__store_ms_login_info(mc_token, uuid, player_name)

	def microsoft_refresh_authenticate(self) -> bool:
		if not self.__mc_auth.has_refresh_token():
			return False
		try:
			mc_token, uuid, player_name = self.__mc_auth.authenticate_with_refresh_token()
			self.__store_ms_login_info(mc_token, uuid, player_name)
			return True
		except AuthenticateException as e:
			self.logger.error('Failed to authenticate with Microsoft with refresh token: {}'.format(e))
			return False

	def __store_ms_login_info(self, mc_token: str, uuid: str, player_name: str):
		self.username = player_name
		self.access_token = mc_token
		self.client_token = uuid4().hex
		self.profile.id_ = uuid
		self.profile.name = player_name

	def mojang_authenticate(self, username: str, password: str):
		self.logger.info('Authenticating with Mojang')
		self.authenticate(username, password)


class MicrosoftAuthenticator:
	"""
	Reference: https://wiki.vg/Microsoft_Authentication_Scheme
	"""
	__JSON_TYPE_HEADER = {
		'Content-Type': 'application/json',
		'Accept': 'application/json'
	}

	def __init__(self, logger: Logger):
		self.logger = logger
		self.__refresh_token: Optional[str] = None

	def has_refresh_token(self) -> bool:
		return self.__refresh_token is not None

	def authenticate(self, auth_code: str) -> Tuple[str, str, str]:
		"""
		:return: mc_token, uuid, player_name
		"""
		access_token, self.__refresh_token = self._get_access_token(access_code=auth_code)
		return self._authenticate_with_access_token(access_token)

	def authenticate_with_refresh_token(self) -> Tuple[str, str, str]:
		"""
		:return: mc_token, uuid, player_name
		"""
		access_token, self.__refresh_token = self._get_access_token(refresh_token=self.__refresh_token)
		return self._authenticate_with_access_token(access_token)

	def _authenticate_with_access_token(self, access_token: str) -> Tuple[str, str, str]:
		xbl_token = self._authenticate_xbl(access_token)
		xsts_token, user_hash = self._authenticate_xsts(xbl_token)
		mc_token = self._authenticate_minecraft(xsts_token, user_hash)
		if not self._check_game_ownership(mc_token):
			raise AuthenticateException('The account doesn\'t own the game')
		uuid, player_name = self._get_uuid(mc_token)
		return mc_token, uuid, player_name

	def _get_access_token(self, *, access_code: Optional[str] = None, refresh_token: Optional[str] = None) -> Tuple[str, str]:
		"""
		:return: access token, refresh token
		"""
		context = {
			'client_id': '00000000402b5328',
			'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
			'scope': 'service::user.auth.xboxlive.com::MBI_SSL'
		}
		if access_code is not None:
			self.logger.info('Getting access token with access code')
			context.update({
				'code': access_code,
				'grant_type': 'authorization_code',
			})
		elif refresh_token is not None:
			self.logger.info('Getting access token with refresh token')
			context.update({
				'refresh_token': refresh_token,
				'grant_type': 'refresh_token',
			})
		else:
			raise ValueError()
		response = requests.post('https://login.live.com/oauth20_token.srf', context)
		if response.status_code == 400:
			raise AuthenticateException(response.json()['error_description'])
		data = response.json()
		return data['access_token'], data['refresh_token']

	def _authenticate_xbl(self, access_token: str) -> str:
		"""
		:return: xbl token, user hash
		"""
		self.logger.info('Authenticating with XBL')
		context = {
			'Properties': {
				"AuthMethod": "RPS",
				'SiteName': 'user.auth.xboxlive.com',
				'RpsTicket': access_token
			},
			'RelyingParty': "http://auth.xboxlive.com",
			'TokenType': 'JWT'
		}
		response = requests.post('https://user.auth.xboxlive.com/user/authenticate', json.dumps(context), headers=self.__JSON_TYPE_HEADER)
		if response.content == b'':
			raise AuthenticateException('Microsoft access token expired')
		else:
			return response.json()['Token']

	def _authenticate_xsts(self, xbl_token: str) -> Tuple[str, str]:
		"""
		:return: xsts token, user hash
		"""
		self.logger.info('Authenticating with XSTS')
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
		response = requests.post('https://xsts.auth.xboxlive.com/xsts/authorize', json.dumps(context), headers=self.__JSON_TYPE_HEADER)
		data = response.json()
		if response.status_code == 401:
			raise AuthenticateException('XSTS Authentication failed: XErr = {}'.format(data['XErr']))
		return data['Token'], data['DisplayClaims']['xui'][0]['uhs']

	def _authenticate_minecraft(self, xsts_token: str, user_hash: str):
		self.logger.info('Authenticating with Minecraft')
		context = {
			'identityToken': 'XBL3.0 x={};{}'.format(user_hash, xsts_token)
		}
		response = requests.post("https://api.minecraftservices.com/authentication/login_with_xbox", json.dumps(context), headers=self.__JSON_TYPE_HEADER)
		return response.json()['access_token']

	def _check_game_ownership(self, mc_token: str) -> bool:
		self.logger.info('Checking Game Ownership')
		headers = dict(Authorization="Bearer {}".format(mc_token))
		res = requests.get("https://api.minecraftservices.com/entitlements/mcstore", headers=headers)
		data = res.json()
		return data.get('items')  # an empty array == False

	def _get_uuid(self, mc_token: str) -> Tuple[str, str]:
		self.logger.info('Getting game profile')
		headers = dict(Authorization="Bearer {}".format(mc_token))
		res = requests.get("https://api.minecraftservices.com/minecraft/profile", headers=headers)
		data = res.json()
		return data['id'], data['name']
