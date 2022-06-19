import json
import os
import time
from abc import ABC, abstractmethod
from threading import Thread, Lock
from typing import TYPE_CHECKING, Optional, Tuple, Type, NamedTuple
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import requests

from minecraft.authentication import AuthenticationToken

if TYPE_CHECKING:
	from pcrc.pcrc_client import PcrcClient


SAVED_TOKEN_FILE = 'token.json'


class AuthenticateException(Exception):
	pass


class AuthType:
	offline = 'offline'
	mojang = 'mojang'
	microsoft = 'microsoft'


class Authenticator(ABC):
	TOKEN_REFRESH_INTERVAL = 3 * 60 * 60  # 3 hours

	def __init__(self, pcrc: 'PcrcClient'):
		self.pcrc = pcrc
		self.logger = pcrc.logger
		self._input_manager = pcrc.input_manager
		self._refresher_thread: Optional[Thread] = None
		self._refresh_lock = Lock()
		self.__has_authenticated = False

		# when PCRC is requested to be unloaded completely (e.g. as MCDR plugin)
		self.__refresh_interrupted = False

	def init(self):
		self.__load_token()

	def _should_store_token(self) -> bool:
		return self.pcrc.config.get('store_token')

	def __load_token(self):
		if self._should_store_token() and os.path.isfile(SAVED_TOKEN_FILE):
			self.logger.info('Loading saved token from {}'.format(SAVED_TOKEN_FILE))
			try:
				with open(SAVED_TOKEN_FILE, 'r', encoding='utf8') as f:
					token_data = json.load(f)
				self._load_token(token_data)
			except Exception as e:
				self.logger.error('Failed to load token from {}: {}'.format(SAVED_TOKEN_FILE, e))
			else:
				if self.is_token_valid() and self.__try_refresh_authentication():
					self._on_authenticated()

	def __save_token(self):
		if self._should_store_token():
			token_data = self._save_token()
			try:
				if token_data is not None:
					with open(SAVED_TOKEN_FILE, 'w', encoding='utf8') as f:
						json.dump(token_data, f, indent=2)
				elif os.path.isfile(SAVED_TOKEN_FILE):
					os.remove(SAVED_TOKEN_FILE)
			except Exception as e:
				self.logger.error('Failed to save token to {}: {}'.format(SAVED_TOKEN_FILE, e))

	@classmethod
	def get_class(cls, auth_type: str) -> Type['Authenticator']:
		if auth_type == AuthType.offline:
			return OfflineAuthenticator
		elif auth_type == AuthType.mojang:
			return MojangAuthenticator
		elif auth_type == AuthType.microsoft:
			return MicrosoftAuthenticator
		else:
			raise ValueError('Unrecognized authenticate type {}'.format(auth_type))

	def has_authenticated(self) -> bool:
		return self.__has_authenticated

	def _on_authenticated(self):
		self.__has_authenticated = True
		self.__save_token()
		self._start_refresh_thread()

	def interrupt_refresh(self):
		self.__refresh_interrupted = True

	def _start_refresh_thread(self):
		def thread_loop():
			while True:
				for i in range(self.TOKEN_REFRESH_INTERVAL):
					if self.__refresh_interrupted:
						return
					time.sleep(1)
				if self.__try_refresh_authentication():
					self.logger.info('Token refreshed')
				else:
					self.__has_authenticated = False
					break
			self._refresher_thread = None

		if self._refresher_thread is None:
			self._refresher_thread = Thread(target=thread_loop, daemon=True, name='TokenRefresher')
			self._refresher_thread.start()

	@property
	@abstractmethod
	def player_name(self) -> str:
		raise NotImplementedError()

	@abstractmethod
	def authenticate(self):
		"""
		Might raises AuthenticateException
		"""
		raise NotImplementedError()

	@abstractmethod
	def _refresh_authentication(self):
		"""
		Might raises AuthenticateException
		"""
		raise NotImplementedError()

	def __try_refresh_authentication(self) -> bool:
		try:
			with self._refresh_lock:
				self._refresh_authentication()
		except Exception as e:
			self.logger.error('Token refresh failed: {}'.format(e))
			return False
		else:
			self.__save_token()
			return True

	@abstractmethod
	def generate_pycraft_token(self) -> Optional[AuthenticationToken]:
		raise NotImplementedError()

	def _save_token(self) -> Optional[dict]:
		return None

	def _load_token(self, data: dict):
		pass

	@abstractmethod
	def is_token_valid(self) -> bool:
		raise NotImplementedError()


class OfflineAuthenticator(Authenticator):
	def __init__(self, pcrc: 'PcrcClient'):
		super().__init__(pcrc)
		self.__player_name = pcrc.config.get('username')

	def has_authenticated(self) -> bool:
		return True

	@property
	def player_name(self) -> str:
		return self.__player_name

	def authenticate(self, start_refresh: bool = True):
		pass

	def _refresh_authentication(self):
		pass

	def _start_refresh_thread(self):
		pass

	def generate_pycraft_token(self) -> Optional[AuthenticationToken]:
		return None

	def is_token_valid(self) -> bool:
		return True


class MojangAuthenticator(Authenticator):
	def __init__(self, pcrc: 'PcrcClient'):
		super().__init__(pcrc)
		self.__pycraft_token = AuthenticationToken()

	@property
	def player_name(self) -> str:
		if not self.has_authenticated():
			raise Exception('Not authenticated')
		return self.__pycraft_token.profile.name

	def authenticate(self, start_refresh: bool = True):
		username, password = self.pcrc.config.get('username'), self.pcrc.config.get('password')
		self.logger.info('(Auth) Authenticating with Mojang')
		self.__pycraft_token.authenticate(username, password)
		self._on_authenticated()

	def _refresh_authentication(self):
		self.logger.info('(Auth) Refreshing token with Mojang')
		self.__pycraft_token.refresh()

	def generate_pycraft_token(self) -> Optional[AuthenticationToken]:
		return self.__pycraft_token

	def is_token_valid(self) -> bool:
		return self.__pycraft_token.authenticated


class MsaToken(NamedTuple):
	expires_at: float
	access_token: str
	refresh_token: str

	def is_expired(self) -> bool:
		return self.expires_at <= time.time()

	def to_dict(self) -> dict:
		return {
			'expires_at': self.expires_at,
			'access_token': self.access_token,
			'refresh_token': self.refresh_token,
		}

	@classmethod
	def from_dict(cls, data: dict) -> 'MsaToken':
		if 'expires_at' not in data and 'expires_in' in data:
			data = data.copy()
			data['expires_at'] = data['expires_in'] + time.time()
		return MsaToken(
			expires_at=data['expires_at'],
			access_token=data['access_token'],
			refresh_token=data['refresh_token'],
		)


class MicrosoftAuthenticator(Authenticator):
	MS_AUTH_URL = 'https://login.live.com/oauth20_authorize.srf?client_id=00000000402b5328&response_type=code&scope=service%3A%3Auser.auth.xboxlive.com%3A%3AMBI_SSL&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf'

	def __init__(self, pcrc: 'PcrcClient'):
		super().__init__(pcrc)
		self.__msa_token: Optional[MsaToken] = None
		self.__mc_token: Optional[str] = None
		self.__player_uuid: Optional[str] = None
		self.__player_name: Optional[str] = None

	def tr(self, key: str, *args, **kwargs) -> str:
		return self.pcrc.tr(key, *args, **kwargs)

	@property
	def player_name(self) -> str:
		if not self.has_authenticated():
			raise Exception('Not authenticated')
		return self.__player_name

	def authenticate(self):
		self.logger.info(self.tr('login.microsoft.url_hint.0'))
		self.logger.info(self.MS_AUTH_URL)
		self.logger.info(self.tr('login.microsoft.url_hint.1'))

		while True:
			user_input = self._input_manager.input(self.tr('login.microsoft.input'))
			queries = parse_qs(urlparse(user_input).query)
			auth_codes = queries.get('code', [])
			if len(auth_codes) != 1:
				self.logger.info(self.tr('login.microsoft.input.invalid'))
			else:
				auth_code = auth_codes[0]
				break

		self.authenticate_with_auth_code(auth_code)
		self._on_authenticated()

	def _refresh_authentication(self):
		if self.__msa_token is None:
			raise RuntimeError('refresh authentication while msa token is None')
		self.logger.info('(Auth) Refreshing token with Microsoft')
		self.authenticate_with_refresh_token(self.__msa_token.refresh_token)

	def generate_pycraft_token(self) -> Optional[AuthenticationToken]:
		token = AuthenticationToken()
		token.username = self.__player_name
		token.access_token = self.__mc_token
		token.client_token = uuid4().hex
		token.profile.id_ = self.__player_uuid
		token.profile.name = self.__player_name
		return token

	def authenticate_with_auth_code(self, auth_code: str):
		self.__msa_token = self.__get_access_token(access_code=auth_code)
		self.__authenticate_with_access_token(self.__msa_token.access_token)

	def authenticate_with_refresh_token(self, refresh_token: str):
		self.__msa_token = self.__get_access_token(refresh_token=refresh_token)
		self.__authenticate_with_access_token(self.__msa_token.access_token)

	def _save_token(self) -> Optional[dict]:
		return self.__msa_token.to_dict()

	def _load_token(self, data: dict):
		msa_token = MsaToken.from_dict(data)
		if msa_token.is_expired():
			self.logger.warning('(Auth) MSA token expired')
		else:
			self.__msa_token = msa_token

	def is_token_valid(self) -> bool:
		return self.__msa_token is not None and not self.__msa_token.is_expired()

	##################################################################
	#                     Implementation Details                     #
	#   Reference: https://wiki.vg/Microsoft_Authentication_Scheme   #
	##################################################################

	__JSON_TYPE_HEADER = {
		'Content-Type': 'application/json',
		'Accept': 'application/json'
	}

	def __authenticate_with_access_token(self, access_token: str):
		xbl_token = self.__authenticate_xbl(access_token)
		xsts_token, user_hash = self.__authenticate_xsts(xbl_token)
		mc_token = self.__authenticate_minecraft(xsts_token, user_hash)
		if not self.__check_game_ownership(mc_token):
			raise AuthenticateException('The account doesn\'t own the game')
		uuid, player_name = self.__get_uuid(mc_token)

		self.__mc_token = mc_token
		self.__player_uuid = uuid
		self.__player_name = player_name

	def __get_access_token(self, *, access_code: Optional[str] = None, refresh_token: Optional[str] = None) -> MsaToken:
		"""
		:return: access token, refresh token
		"""
		context = {
			'client_id': '00000000402b5328',
			'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
			'scope': 'service::user.auth.xboxlive.com::MBI_SSL'
		}
		if access_code is not None:
			self.logger.info('(Auth) Getting access token with access code')
			context.update({
				'code': access_code,
				'grant_type': 'authorization_code',
			})
		elif refresh_token is not None:
			self.logger.info('(Auth) Getting access token with refresh token')
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
		return MsaToken.from_dict(data)

	def __authenticate_xbl(self, access_token: str) -> str:
		"""
		:return: xbl token, user hash
		"""
		self.logger.info('(Auth) Authenticating with XBL')
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

	def __authenticate_xsts(self, xbl_token: str) -> Tuple[str, str]:
		"""
		:return: xsts token, user hash
		"""
		self.logger.info('(Auth) Authenticating with XSTS')
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

	def __authenticate_minecraft(self, xsts_token: str, user_hash: str):
		self.logger.info('(Auth) Authenticating with Minecraft')
		context = {
			'identityToken': 'XBL3.0 x={};{}'.format(user_hash, xsts_token)
		}
		response = requests.post("https://api.minecraftservices.com/authentication/login_with_xbox", json.dumps(context), headers=self.__JSON_TYPE_HEADER)
		return response.json()['access_token']

	def __check_game_ownership(self, mc_token: str) -> bool:
		self.logger.info('(Auth) Checking Game Ownership')
		headers = dict(Authorization="Bearer {}".format(mc_token))
		res = requests.get("https://api.minecraftservices.com/entitlements/mcstore", headers=headers)
		data = res.json()
		return data.get('items')  # an empty array == False

	def __get_uuid(self, mc_token: str) -> Tuple[str, str]:
		self.logger.info('(Auth) Getting game profile')
		headers = dict(Authorization="Bearer {}".format(mc_token))
		res = requests.get("https://api.minecraftservices.com/minecraft/profile", headers=headers)
		data = res.json()
		return data['id'], data['name']
