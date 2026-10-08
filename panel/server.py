import asyncio, secrets, uuid, json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from configuration import ROOT, Settings, Action
from services.events import Event
from services.secrets import save_key, load_key
from services.tiktok_service import TikTokService

class Credentials(BaseModel):
    username: str = Field('', max_length=80)
    key: str = Field('', max_length=1024)

class SaveKeyPayload(BaseModel):
    key: str = Field('', max_length=1024)

class Simulation(BaseModel):
    action: Action = 'BUILD'
    kind: str = Field('gift', pattern='^(gift|like|follow|comment|share)$')
    name: str = Field('Bruno', min_length=1, max_length=40)
    avatar: str = Field('', max_length=2048)
    count: int = Field(1, ge=1, le=10000)
    combo: bool = False
    comment: str = Field('construir', max_length=200)

def is_valid_local_origin(origin: str | None) -> bool:
    if not origin:
        return True
    origin_clean = origin.rstrip('/').lower()
    allowed_prefixes = (
        'http://127.0.0.1',
        'http://localhost',
        'http://testserver',
        'http://[::1]',
        'https://127.0.0.1',
        'https://localhost'
    )
    return origin_clean.startswith(allowed_prefixes)

def make_app(runtime):
    token = secrets.token_urlsafe(32)
    live = TikTokService(runtime.submit_event)
    edit_lock = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app):
        yield
        await live.stop()

    app = FastAPI(docs_url=None, redoc_url=None, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['*'])

    @app.middleware('http')
    async def local_guard(req: Request, call_next):
        if req.method not in ('GET', 'HEAD'):
            origin = req.headers.get('origin')
            req_token = req.headers.get('x-b7-token')
            if req_token != token or not is_valid_local_origin(origin):
                return JSONResponse({'detail': 'Origem local ou sessão inválida. Reabra o painel.'}, 403)
        response = await call_next(req)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' data: blob:; img-src 'self' data: https: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss: http: https:; frame-ancestors 'none'"
        return response

    def state():
        s = runtime.snapshot()
        s['connection'] = live.snapshot()
        saved = load_key()
        s['key_saved'] = bool(saved)
        s['key_preview'] = ('••••••••' + saved[-4:]) if (saved and len(saved) > 4) else ('••••' if saved else '')
        return s

    async def command(name, data=None):
        try:
            f = runtime.command(name, data)
            return await asyncio.wait_for(asyncio.wrap_future(f), 5)
        except asyncio.TimeoutError:
            raise HTTPException(503, 'O jogo não respondeu. Confira a janela do jogo.')
        except Exception as e:
            raise HTTPException(400, str(e))

    @app.get('/')
    async def index():
        return FileResponse(ROOT / 'panel/index.html')

    @app.get('/api/session')
    async def session():
        return {'token': token}

    @app.get('/api/state')
    async def get_state():
        return state()

    @app.post('/api/save-key')
    async def save_euler_key(payload: SaveKeyPayload):
        async with edit_lock:
            key = payload.key.strip()
            if not key:
                raise HTTPException(400, 'Informe uma chave Euler válida.')
            save_key(key)
            return {'ok': True, 'key_saved': True, 'message': 'Chave Euler salva com sucesso!'}

    @app.post('/api/settings')
    async def settings(cfg: Settings):
        async with edit_lock:
            try:
                cfg.checked()
            except ValueError as exc:
                raise HTTPException(400, str(exc))
            previous = runtime.snapshot()['config']
            if previous['mode'] != cfg.mode and cfg.mode == 'test':
                await live.stop()
            return await command('settings', cfg.model_dump())

    @app.post('/api/game/{action}')
    async def game(action: str):
        if action not in ('start', 'pause', 'restart', 'reset'):
            raise HTTPException(404)
        return await command('restart' if action == 'reset' else action, action == 'reset')

    @app.post('/api/connect')
    async def connect(credentials: Credentials):
        async with edit_lock:
            snap = runtime.snapshot()
            cfg = Settings.model_validate(snap['config'])
            username = credentials.username.strip()
            if username:
                cfg.username = username
            try:
                cfg = Settings.model_validate(cfg.model_dump()).checked()
            except ValueError:
                raise HTTPException(400, 'Use somente o @ do TikTok, sem URL ou espaços.')

            key = credentials.key.strip() or load_key()
            if not key:
                raise HTTPException(400, 'Informe a Chave Euler para conectar à live.')
            if not cfg.username:
                raise HTTPException(400, 'Informe o @ do canal TikTok da live.')

            # If there's an ongoing connection or task, stop cleanly first
            if live.task and not live.task.done():
                await live.stop()

            # If the user provided a key explicitly, save it
            if credentials.key.strip():
                save_key(credentials.key.strip())

            cfg.mode = 'live'
            await command('settings', cfg.model_dump())
            await live.start(cfg.username, key)
            return {'ok': True, 'key_saved': True}

    @app.post('/api/disconnect')
    async def disconnect():
        await live.stop()
        return {'ok': True}

    @app.post('/api/test-disconnect')
    async def drop():
        return {'message': await live.test_disconnect()}

    @app.post('/api/simulate')
    async def simulate(sim: Simulation):
        if runtime.snapshot()['config']['mode'] != 'test':
            raise HTTPException(409, 'Ative o modo Teste antes de simular.')
        group = uuid.uuid4().hex
        results = []
        counts = sorted(set([1, max(1, sim.count // 2), sim.count])) + [sim.count] if sim.combo else [sim.count]
        for i, count in enumerate(counts):
            e = Event(
                kind=sim.kind,
                id=uuid.uuid4().hex,
                user_id='test:' + sim.name,
                name=sim.name,
                avatar=sim.avatar,
                count=count,
                test_action=sim.action,
                gift_name='Teste ' + sim.action,
                combo_id=group if sim.combo else '',
                streakable=sim.combo,
                final=i == len(counts) - 1,
                comment=sim.comment
            )
            results.append(await command('event', e))
        return {'ok': True, 'applied': [r for r in results if r]}

    @app.websocket('/ws')
    async def ws(socket: WebSocket):
        origin = socket.headers.get('origin')
        if not is_valid_local_origin(origin):
            await socket.close(code=1008)
            return
        await socket.accept()
        try:
            auth = await asyncio.wait_for(socket.receive_json(), 5)
            if auth.get('token') != token:
                await socket.close(code=1008)
                return
            while True:
                await socket.send_json(state())
                await asyncio.sleep(0.4)
        except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
            pass

    app.mount('/static', StaticFiles(directory=ROOT / 'panel'), name='static')
    app.mount('/assets', StaticFiles(directory=ROOT / 'assets'), name='assets')
    app.state.live = live
    return app
