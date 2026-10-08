from TikTokLive.events import GiftEvent,LikeEvent
from TikTokLive.proto import User,Gift,ImageModel,CommonMessageData
from services.tiktok_service import normalized,friendly_error

def test_actual_library_payload_normalization():
 gift=Gift(id=123,type=1,name='Teste',image=ImageModel(url_list=['https://example.org/gift.png']))
 user=User(id=99,nickname='Ana',avatar_thumb=ImageModel(url_list=['https://example.org/a.png']))
 event=GiftEvent(gift_id=123,gift=gift,user=user,repeat_count=4,repeat_end=0,group_id=77,common=CommonMessageData(msg_id=11))
 e=normalized('gift',event,'room')
 assert e.count==4 and e.combo_id=='room:77' and e.id=='room:11'
 assert e.name=='Ana' and e.streakable and not e.final and e.source=='live'
 event.repeat_end=1;assert normalized('gift',event).final
 like=LikeEvent(count=17,user=user);assert normalized('like',like).count==17

def test_error_does_not_leak_secrets():
 message=friendly_error(RuntimeError('https://host?key=MY_SECRET'))
 assert 'MY_SECRET' not in message and 'https' not in message

def test_reconnection_bounded_and_game_independent():
 import asyncio,types
 from services.tiktok_service import TikTokService
 attempts=[];delays=[]
 class BrokenTransport:
  def __init__(self,**kwargs):self.logger=types.SimpleNamespace(disabled=False);attempts.append(1)
  def add_listener(self,*args):pass
  async def connect(self,**kwargs):raise TimeoutError('fake')
  async def disconnect(self,**kwargs):pass
 async def no_wait(seconds):delays.append(seconds)
 async def run():
  service=TikTokService(lambda e:None,client_factory=BrokenTransport,sleep=no_wait)
  await service.start('test_account','offline-test-value')
  await service.task
  assert service.status=='error' and len(attempts)==8
  assert delays==[2,4,8,16,32,60,60]
  await service.stop();assert service.status=='offline'
 asyncio.run(run())

def test_avatar_failure_fallback_is_nonblocking(monkeypatch):
 import time
 from services.avatars import AvatarCache
 import services.avatars as module
 # Simulated DNS/network failure; no external request is performed by this test.
 def failure(*args,**kwargs):raise OSError('offline')
 monkeypatch.setattr(module.socket,'getaddrinfo',failure)
 cache=AvatarCache();start=time.monotonic()
 for i in range(100):cache.request(f'https://invalid.example/{i}.jpg')
 assert time.monotonic()-start<.5
 assert cache.worker.is_alive() and len(cache.known)<=256
 cache.closed.set();cache.worker.join(timeout=1)
