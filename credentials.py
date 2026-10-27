"""Windows user-bound encryption for local sandbox credentials; env vars also work."""
import ctypes
import json
import os
from pathlib import Path

FILE = Path(__file__).resolve().parent / 'data' / 'sandbox-credentials.bin'


class Blob(ctypes.Structure):
    _fields_ = [('size', ctypes.c_uint32), ('data', ctypes.c_void_p)]


def protect(data, decrypt=False):
    if os.name != 'nt':
        raise ValueError('Encrypted credential storage is Windows-only; use environment variables here')
    buffer = ctypes.create_string_buffer(data)
    source, output = Blob(len(data), ctypes.cast(buffer, ctypes.c_void_p)), Blob()
    function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(output.data)


def save(value):
    plaintext = json.dumps(value).encode()
    encrypted = protect(plaintext)
    if protect(encrypted, decrypt=True) != plaintext:
        raise ValueError('Credential encryption verification failed')
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_bytes(encrypted)


def load():
    client = os.environ.get('PAYPAL_SANDBOX_CLIENT_ID')
    secret = os.environ.get('PAYPAL_SANDBOX_CLIENT_SECRET')
    if client and secret:
        return client, secret
    if FILE.exists():
        value = json.loads(protect(FILE.read_bytes(), decrypt=True))
        return value['client_id'], value['client_secret']
    raise ValueError('Configure local sandbox credentials or set PAYPAL_SANDBOX_CLIENT_ID and PAYPAL_SANDBOX_CLIENT_SECRET')
