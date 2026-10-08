"""Bounded background image loader. Rendering and downloads never share pygame objects."""
import io, queue, threading, ipaddress, socket
from collections import OrderedDict
from urllib.parse import urlsplit
from PIL import Image
import httpx
Image.MAX_IMAGE_PIXELS=4_000_000
class AvatarCache:
    def __init__(self):
        self.requests=queue.Queue(32);self.ready=queue.Queue(64)
        self.known=OrderedDict();self.closed=threading.Event()
        self.worker=threading.Thread(target=self.run,daemon=True);self.worker.start()
    def request(self,url):
        if not url or url in self.known:return
        if not str(url).startswith('https://'):return
        try:self.requests.put_nowait(url)
        except queue.Full:return
        self.known[url]=True
        while len(self.known)>256:self.known.popitem(last=False)
    def run(self):
        with httpx.Client(timeout=4,follow_redirects=False,trust_env=False) as client:
            while not self.closed.is_set():
                try:url=self.requests.get(timeout=.5)
                except queue.Empty:continue
                try:
                    host=urlsplit(url).hostname
                    if not host:continue
                    addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
                    if any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):continue
                    with client.stream('GET',url) as response:
                        response.raise_for_status();raw=bytearray()
                        for chunk in response.iter_bytes():
                            raw.extend(chunk)
                            if len(raw)>2_000_000:raise ValueError('Image too large')
                    with Image.open(io.BytesIO(raw)) as im:
                        im=im.convert('RGBA');im.thumbnail((64,64));bg=Image.new('RGBA',(64,64))
                        bg.paste(im,((64-im.width)//2,(64-im.height)//2))
                        self.ready.put_nowait((url,bg.tobytes()))
                except Exception:pass  # Avatar failures are intentionally non-fatal.
