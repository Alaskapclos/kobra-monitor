# SPDX-License-Identifier: GPL-3.0-only
"""One local owner account. Passwords are never stored in plain text."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import unicodedata

PARAMS = {'n': 32768, 'r': 8, 'p': 3}

def username(value):
    if not isinstance(value, str):
        raise ValueError('Bitte einen Benutzernamen eingeben.')
    value = unicodedata.normalize('NFKC', value).strip()
    if not 3 <= len(value) <= 64 or any(not c.isprintable() for c in value):
        raise ValueError('Der Benutzername braucht 3 bis 64 druckbare Zeichen.')
    return value

def password(value):
    if not isinstance(value, str) or not 15 <= len(value) <= 128:
        raise ValueError('Das Passwort braucht 15 bis 128 Zeichen. Ein langer Satz ist gut geeignet.')
    return value

def derive(value, salt):
    return hashlib.scrypt(value.encode('utf-8'), salt=salt, **PARAMS,
                          maxmem=64 * 1024 * 1024, dklen=32).hex()

def read_account(directory):
    path = Path(directory) / 'account.json'
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text())
        if (value['version'] != 1 or value['algorithm'] != 'scrypt'
                or value['parameters'] != PARAMS or username(value['username']) != value['username']
                or len(bytes.fromhex(value['salt'])) != 16
                or len(bytes.fromhex(value['password_hash'])) != 32):
            raise ValueError()
        return value
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ValueError('Die lokale Kontodatei ist ungültig. Bitte aus einer Sicherung wiederherstellen.') from exc

def matches(account, name, secret):
    # Do the same password work even for an unknown user name.
    valid = isinstance(secret, str) and len(secret) <= 128
    actual = derive(secret if valid else '', bytes.fromhex(account['salt']))
    try:
        same_name = username(name).casefold() == account['username'].casefold()
    except ValueError:
        same_name = False
    return valid and hmac.compare_digest(actual, account['password_hash']) and same_name

def write_account(directory, name, secret):
    name, secret = username(name), password(secret)
    salt = secrets.token_bytes(16)
    value = {'version': 1, 'username': name, 'algorithm': 'scrypt', 'parameters': PARAMS,
             'salt': salt.hex(), 'password_hash': derive(secret, salt)}
    directory = Path(directory)
    descriptor, temporary = tempfile.mkstemp(prefix='.account-', dir=directory)
    try:
        with os.fdopen(descriptor, 'w') as out:
            out.write(json.dumps(value) + '\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, directory / 'account.json')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return value
