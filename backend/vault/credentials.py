"""Encrypted credential vault — Fernet AES-128."""
import json, os
from cryptography.fernet import Fernet
from backend.config import Config


def _master_key():
    k = Config.VAULT_MASTER_KEY
    if k:
        return k.encode() if isinstance(k, str) else k
    kf = Config.VAULT_DIR / "master.key"
    if kf.exists():
        return kf.read_bytes().strip()
    nk = Fernet.generate_key()
    kf.write_bytes(nk)
    try: os.chmod(kf, 0o600)
    except: pass
    (Config.VAULT_DIR / "MASTER_KEY_GENERATED.txt").write_text(
        f"VAULT_MASTER_KEY={nk.decode()}\n"
    )
    print(f"[vault] generated key at {kf}")
    return nk


def _f(): return Fernet(_master_key())
def _vf(): return Config.VAULT_DIR / "creds.enc"


def _read():
    p = _vf()
    if not p.exists(): return {}
    try: return json.loads(_f().decrypt(p.read_bytes()).decode())
    except: return {}


def _write(d):
    _vf().write_bytes(_f().encrypt(json.dumps(d).encode()))


def store(name, value, engagement="default"):
    d = _read()
    d.setdefault(engagement, {})[name] = value
    _write(d)


def fetch(name, engagement="default"):
    return _read().get(engagement, {}).get(name)


def list_creds(engagement="default"):
    return list(_read().get(engagement, {}).keys())


def delete(name, engagement="default"):
    d = _read()
    if engagement in d and name in d[engagement]:
        del d[engagement][name]
        _write(d)
        return True
    return False
