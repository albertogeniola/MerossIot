import logging
from hashlib import md5
import base64
from Cryptodome.Cipher import AES
from enum import Enum
from typing import Dict

from meross_iot.controller.device import BaseDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class EncryptionAlg(Enum):
    ECDHE256 = 0


class EncryptionSuiteMixin(BaseDevice):
    _execute_command: callable
    __encryption_default_iv = "0000000000000000".encode("utf8")
    _abilities: Dict[str, dict]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self.__encryption_key = None

        # Check if the device supports ECDHE256 encryption
        if Namespace.SYSTEM_ENCRYPTION_ECDHE.value in self._abilities:
            self.__encryption_alg = EncryptionAlg.ECDHE256
        else:
            raise ValueError("Unsupported/undetected encryption method")

    def __encryption_pad_to_16_bytes(self, data):
        block_size = 16
        pad_length = block_size - (len(data) % block_size)
        padding = bytes([0] * pad_length)
        return data + padding

    def __encryption_ecdhe256_encrypt(self, message_data_bytes, iv=None) -> str:
        if iv is None:
            iv = self.__encryption_default_iv
        # Returns encrypted message in base64 encoded string.
        padded_data = self.__encryption_pad_to_16_bytes(message_data_bytes)
        cipher = AES.new(self.__encryption_key, AES.MODE_CBC, iv)
        cipher.padding = 0
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted).decode('utf-8')

    def __encryption_ecdhe256_decrypt(self, message_data_bytes: bytes, iv=None) -> bytes:
        if iv is None:
            iv = self.__encryption_default_iv
        # Returns decrypted message bytes.
        cipher = AES.new(self.__encryption_key, AES.MODE_CBC, iv)
        cipher.padding = 0
        enc_bytes = base64.b64decode(message_data_bytes)
        decrypted = cipher.decrypt(enc_bytes)
        return decrypted

    @property
    def encryption_supported(self) -> bool:
        return True

    @property
    def encryption_key_set(self) -> bool:
        return self.__encryption_key is not None

    def encryption_set_key(self, uuid: str, mrskey: str, mac: str, *args, **kwargs):
        """
        Sets the encryption key
        :param uuid:
        :param mrskey:
        :param mac:
        :param args:
        :param kwargs:
        :return:
        """
        strtohash = uuid[3:22] + mrskey[1:9] + mac + mrskey[10:28]
        self.__encryption_key = md5(strtohash.encode("utf8")).hexdigest().encode("utf8")

    def encryption_encrypt(self, message_data_bytes: bytes) -> str:
        """
        Encrypts the message into a base64 string
        :param message_data_bytes:
        :return:
        """
        if not self.encryption_key_set:
            raise ValueError("Encryption key is not set! Please invoke set_encryption_key first.")

        if self.__encryption_alg == EncryptionAlg.ECDHE256:
            return self.__encryption_ecdhe256_encrypt(message_data_bytes)

        raise ValueError("Unimplemented encryption algorithm")

    def encryption_decrypt(self, encrypted_message_bytes: bytes) -> bytes:
        """
        Decrypt the message and returns the war decrypted bytes
        :param encrypted_message_bytes:
        :return:
        """
        if not self.encryption_key_set:
            raise ValueError("Encryption key is not set! Please invoke set_encryption_key first.")

        if self.__encryption_alg == EncryptionAlg.ECDHE256:
            return self.__encryption_ecdhe256_decrypt(encrypted_message_bytes)

        raise ValueError("Unimplemented encryption algorithm")
