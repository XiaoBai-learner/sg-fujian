"""Encrypt saved connection passwords; keep the local key outside the database."""
import os
from cryptography.fernet import Fernet, InvalidToken

def credential_box(storage):
    path=storage.root / '.connection-key'
    try:
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor,'wb') as stream: stream.write(Fernet.generate_key())
    return Fernet(path.read_bytes())

def decrypt_password(storage, value):
    try: return credential_box(storage).decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, OSError) as error:
        raise ValueError('连接凭据无法解密，请重新编辑并保存密码') from error
