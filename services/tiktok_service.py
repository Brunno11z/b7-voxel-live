"""TikTokLive 7.0.1 adapter using Euler's documented signing-key configuration.
Docs: https://www.eulerstream.com/docs/api-key-usage/python
No endpoint is constructed by this application. Network handled by TikTokLive.
"""
import asyncio,logging,time
from services.events import Event

def image_url(image):
    urls=getattr(image,'url_list',None) or []
    return str(urls[0]) if urls else ''
def normalized(kind,event,room=''):
    user=getattr(event,'user',None);common=getattr(event,'common',None)
    msg=str(getattr(common,'msg_id',0) or '')
    e=Event(kind=kind,source='live',id=f'{room}:{msg}' if msg else '',
            user_id=str(getattr(user,'id',0) or getattr(user,'unique_id','unknown')),
            name=str(getattr(user,'nickname','Visitante') or 'Visitante'),
            avatar=image_url(getattr(user,'avatar_thumb',None)))
    if kind=='gift':
        gift=getattr(event,'gift',None)
        e.gift_id=str(getattr(event,'gift_id',0) or getattr(gift,'id',0));e.gift_name=str(getattr(gift,'name',''))
        e.gift_icon=image_url(getattr(gift,'image',None));e.count=max(1,int(getattr(event,'repeat_count',1) or 1))
        e.streakable=getattr(gift,'type',0)==1;e.final=not bool(getattr(event,'streaking',False))
        group=getattr(event,'group_id',0);e.combo_id=f'{room}:{group}' if group else ''
    elif kind=='like':e.count=max(1,int(getattr(event,'count',1) or 1))
    elif kind=='comment':e.comment=str(getattr(event,'comment',''))[:200]
    return e

def friendly_error(exc):
    # Never return exception bodies or URLs; upstream messages can contain credentials.
    name=type(exc).__name__;n=name.lower()
    if 'offline' in n or 'usernotfound' in n:return 'Live offline ou usuário não encontrado.'
    if any(s in n for s in ('sign','auth','credential','api')):return 'Falha de autenticação/assinatura. Confira a chave, plano e limites Euler.'
    if 'rate' in n:return 'Limite de conexões atingido. Aguarde antes de tentar novamente.'
    if 'timeout' in n:return 'Tempo de conexão esgotado. Confira a internet.'
    return f'Conexão interrompida ({name}). Confira a live, a internet e a chave Euler.'

class TikTokService:
    def __init__(self,submit,client_factory=None,sleep=asyncio.sleep):
        self.submit=submit;self.client_factory=client_factory;self.sleep=sleep;self.task=None;self.client=None;self.stop_requested=True
        self.status='offline';self.message='Modo de teste disponível.';self.attempt=0;self.received=0
    def snapshot(self):return dict(status=self.status,message=self.message,attempt=self.attempt,received=self.received)
    async def start(self,username,key):
        if self.task and not self.task.done():raise ValueError('Já existe uma conexão ativa ou em andamento.')
        if not username or not key:raise ValueError('Informe o @ da live e a chave Euler.')
        self.stop_requested=False;self.task=asyncio.create_task(self.run(username,key))
    async def stop(self):
        self.stop_requested=True
        if self.client:
            try:await asyncio.wait_for(self.client.disconnect(close_client=True),3)
            except Exception:pass
        if self.task and not self.task.done():
            self.task.cancel()
            try:await asyncio.wait_for(self.task,4)
            except (asyncio.CancelledError,asyncio.TimeoutError):pass
        self.client=None;self.status='offline';self.message='Desconectado.'
    async def run(self,username,key):
        from TikTokLive import TikTokLiveClient
        from TikTokLive.client.web.web_settings import WebDefaults
        from TikTokLive.events import ConnectEvent,GiftEvent,LikeEvent,CommentEvent,FollowEvent,ShareEvent
        logging.getLogger('TikTokLive').disabled=True
        WebDefaults.tiktok_sign_api_key=key
        try:
            for attempt in range(1,9):
                if self.stop_requested:break
                self.attempt=attempt;self.status='connecting';self.message=f'Conectando a @{username.lstrip("@")}…'
                client=(self.client_factory or TikTokLiveClient)(unique_id=username);self.client=client;client.logger.disabled=True
                async def connected(event):
                    self.status='connected';self.message='Conectado. Eventos da live ativos.'
                client.add_listener(ConnectEvent,connected)
                for event_type,kind in [(GiftEvent,'gift'),(LikeEvent,'like'),(CommentEvent,'comment'),(FollowEvent,'follow'),(ShareEvent,'share')]:
                    async def handler(event,kind=kind):
                        try:
                            e=normalized(kind,event,str(client.room_id or ''));self.submit(e);self.received+=1
                        except Exception:
                            self.message='Fila cheia ou evento inválido. Confira o diagnóstico no painel.'
                    client.add_listener(event_type,handler)
                try:
                    await client.connect(fetch_gift_info=False)
                    if not self.stop_requested:self.message='Live desconectada; aguardando nova tentativa.'
                except asyncio.CancelledError:raise
                except Exception as exc:self.message=friendly_error(exc)
                finally:
                    try:await asyncio.wait_for(client.disconnect(close_client=True),3)
                    except (Exception,asyncio.CancelledError):pass
                    self.client=None
                if self.stop_requested:break
                if attempt==8:self.status='error';self.message+=' Limite de 8 tentativas; use Conectar para tentar novamente.';return
                delay=min(60,2**attempt);self.status='reconnecting'
                self.message+=f' Nova tentativa em {delay}s.'
                await self.sleep(delay)
        except asyncio.CancelledError:pass
        finally:
            if self.stop_requested:self.status='offline'
    async def test_disconnect(self):
        # Real active connection: simulate a transport drop, keep reconnection enabled.
        if self.client and self.status=='connected':
            await self.client.disconnect();return 'Conexão interrompida; reconexão automática acionada.'
        return 'Sem conexão ativa. O jogo offline continua funcionando.'
