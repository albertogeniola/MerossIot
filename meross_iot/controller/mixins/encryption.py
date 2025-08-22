import logging
from hashlib import md5
import base64
from Cryptodome.Cipher import AES
from enum import Enum
from typing import Dict
from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class EncryptionAlg(Enum):
    ECDHE256 = 0


class EncryptionSuiteMixin(DynamicFilteringMixin):
    _execute_command: callable
    _DEFAULT_IV="0000000000000000".encode("utf8")
    _abilities: Dict[str, dict]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self._encryption_key = None

        if Namespace.SYSTEM_ENCRYPTION_ECDHE.value in self._abilities:
            self._encryption_alg = EncryptionAlg.ECDHE256
        else:
            raise ValueError("Unsupported/undetected encryption method")
        
    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.SYSTEM_ENCRYPTION.value
    
    def _pad_to_16_bytes(self, data):
        block_size = 16
        pad_length = block_size - (len(data) % block_size)
        padding = bytes([0] * pad_length)
        return data + padding

    def _ecdhe256_encrypt(self, message_data_bytes, iv=_DEFAULT_IV) -> str:
        # Returns encrypted message in base64 encoded string.
        padded_data = self._pad_to_16_bytes(message_data_bytes)
        cipher = AES.new(self._encryption_key, AES.MODE_CBC, iv)
        cipher.padding = 0
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted).decode('utf-8')

    def _ecdhe256_decrypt(self, message_data_bytes: bytes, iv=_DEFAULT_IV) -> bytes:
        # Returns decrypted message bytes.
        cipher = AES.new(self._encryption_key, AES.MODE_CBC, iv)
        cipher.padding = 0
        enc_bytes = base64.b64decode(message_data_bytes)
        decrypted = cipher.decrypt(enc_bytes)
        return decrypted

    def support_encryption(self) -> bool:
        return True

    def is_encryption_key_set(self) -> bool:
        return self._encryption_key is not None

    def set_encryption_key(self, uuid:str, mrskey: str, mac: str, *args, **kwargs):
        strtohash = uuid[3:22] + mrskey[1:9] + mac + mrskey[10:28]
        self._encryption_key = md5(strtohash.encode("utf8")).hexdigest().encode("utf8")

    def encrypt(self, message_data_bytes: bytes)->str:
        """
        Encrypts the message into a base64 string
        :param message_data_bytes:
        :return:
        """
        if not self.is_encryption_key_set():
            raise ValueError("Encryption key is not set! Please invoke set_encryption_key first.")

        if self._encryption_alg == EncryptionAlg.ECDHE256:
            return self._ecdhe256_encrypt(message_data_bytes)

        raise ValueError("Unimplemented encryption algorithm")

    def decrypt(self, encrypted_message_bytes: bytes) -> bytes:
        """
        Decrypt the message and returns the war decrypted bytes
        :param encrypted_message_bytes:
        :return:
        """
        if not self.is_encryption_key_set():
            raise ValueError("Encryption key is not set! Please invoke set_encryption_key first.")

        if self._encryption_alg == EncryptionAlg.ECDHE256:
            return self._ecdhe256_decrypt(encrypted_message_bytes)

        raise ValueError("Unimplemented encryption algorithm")