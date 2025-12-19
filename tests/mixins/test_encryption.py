from typing import Any, Generator, Dict

import pytest
from meross_iot.controller.mixins.encryption import EncryptionSuiteMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[EncryptionSuiteMixin, Any, None]:
    abilities = {
        Namespace.SYSTEM_ENCRYPTION_ECDHE.value: {}
    }
    
    # Create a dynamic class that has _abilities_spec to mock how device_factory works
    class TestEncryptionDevice(EncryptionSuiteMixin):
        _abilities_spec = abilities

    mixin = TestEncryptionDevice(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield mixin


def test_initialization(device: EncryptionSuiteMixin):
    assert device.encryption_supported
    assert not device.encryption_key_set


def test_set_key_and_encrypt_decrypt(device: EncryptionSuiteMixin):
    uuid = "11111111111111111111111111111111"
    mrskey = "139185119790641d6a39d0c68361539d"
    mac = "a1:a1:a1:a1:a1:a1"
    
    device.encryption_set_key(uuid=uuid, mrskey=mrskey, mac=mac)
    assert device.encryption_key_set
    
    # Test encrypt/decrypt
    message = b"hello world"
    # Encrypt
    encrypted = device.encryption_encrypt(message)
    # The result should be base64 string
    assert isinstance(encrypted, str)
    # Ensure the encrypted message is what we expect to be.
    # This string has been provided by calculated with an external script that is complaint with the
    # Merross encryption system
    assert encrypted == 'Uw/SMrmaUZZsEppMC3/QIQ=='

    # Decrypt
    decrypted = device.encryption_decrypt(encrypted)
    # The result should be bytes
    # Note: The current implementation uses zero-padding and does NOT strip it upon decryption.
    # So we strip it here for verification.
    assert decrypted.rstrip(b'\0') == message


def test_initialization_failure(manager_mock: MerossManager, replacer_mock: Dict[str, Any]):
    # Test that it fails if ability is missing
    with pytest.raises(ValueError):
        EncryptionSuiteMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock, abilities={})


def test_encrypt_decrypt_no_key(device: EncryptionSuiteMixin):
    # Ensure it raises ValueError if key is not set
    assert not device.encryption_key_set
    with pytest.raises(ValueError):
        device.encryption_encrypt(b"test")
    with pytest.raises(ValueError):
        device.encryption_decrypt(b"test")


def test_unknown_algorithm(device: EncryptionSuiteMixin, replacer_mock: Dict[str, Any]):
    uuid = "11111111111111111111111111111111"
    mrskey = "139185119790641d6a39d0c68361539d"
    mac = "a1:a1:a1:a1:a1:a1"
    device.encryption_set_key(uuid=uuid, mrskey=mrskey, mac=mac)
    
    # Tamper with internal state to simulate unknown algorithm
    # Name mangling: _EncryptionSuiteMixin__encryption_alg
    device._EncryptionSuiteMixin__encryption_alg = -1  # Invalid enum value or just int
    
    with pytest.raises(ValueError, match="Unimplemented encryption algorithm"):
        device.encryption_encrypt(b"test")
        
    with pytest.raises(ValueError, match="Unimplemented encryption algorithm"):
        device.encryption_decrypt(b"test")
