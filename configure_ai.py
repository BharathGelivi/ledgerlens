"""Prompt locally for an NVIDIA API key and store it with Windows user encryption."""
import getpass
import json
import re

from credentials import FILE, protect

AI_FILE = FILE.with_name('ai-credentials.bin')
DEFAULT_MODEL = 'nvidia/nemotron-3.5-lightning-30b-a3b'


def load_ai():
    if not AI_FILE.exists():
        return None
    return json.loads(protect(AI_FILE.read_bytes(), decrypt=True))


def configure(key, model=DEFAULT_MODEL):
    key = key.strip()
    if not key.startswith('nvapi-') or len(key) < 30 or any(c.isspace() for c in key):
        raise ValueError('This does not look like an NVIDIA API key; nothing saved')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', model):
        raise ValueError('Enter a model identifier in organization/model format')
    content = json.dumps({'provider': 'nvidia', 'api_key': key, 'model': model}).encode()
    encrypted = protect(content)
    if protect(encrypted, decrypt=True) != content:
        raise ValueError('Encryption check failed; nothing saved')
    AI_FILE.parent.mkdir(parents=True, exist_ok=True)
    AI_FILE.write_bytes(encrypted)


if __name__ == '__main__':
    print('LedgerLens NVIDIA setup. The key is hidden as you paste it.')
    print('This saves an encrypted local file. It makes no API call.')
    configure(getpass.getpass('NVIDIA API key: '))
    print('Saved. Return to LedgerLens and refresh the page; no server restart is needed.')
