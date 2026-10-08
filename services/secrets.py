"""Windows DPAPI, scoped to the current user; permission-restricted fallback on Linux."""
import ctypes, os
from pathlib import Path
from configuration import ROOT
PATH=ROOT/'config/euler.secret'
def _dpapi(raw,decrypt=False):
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    buf=ctypes.create_string_buffer(raw);src=Blob(len(raw),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte)));dst=Blob()
    func=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not func(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)):raise ctypes.WinError()
    try:return ctypes.string_at(dst.pbData,dst.cbData)
    finally:ctypes.windll.kernel32.LocalFree(dst.pbData)
def save_key(key):
    if not key: return
    PATH.parent.mkdir(parents=True,exist_ok=True)
    raw=key.strip().encode();raw=_dpapi(raw) if os.name=='nt' else raw
    temp=PATH.with_suffix('.tmp');temp.write_bytes(raw)
    if os.name!='nt':temp.chmod(0o600)
    os.replace(temp,PATH)
def load_key():
    if os.environ.get('EULER_API_KEY'):return os.environ['EULER_API_KEY'].strip()
    if not PATH.exists():return ''
    try:
        raw=PATH.read_bytes();return (_dpapi(raw,True) if os.name=='nt' else raw).decode()
    except Exception:return ''
