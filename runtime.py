import threading, queue, copy, time
from concurrent.futures import Future
from collections import deque
from configuration import Settings, atomic_json, ROOT
from game.model import World
from services.events import EventRouter

class Runtime:
    def __init__(self, cfg, path=None):
        self.world = World(cfg)
        self.router = EventRouter(self.world)
        self.commands = queue.Queue(4096)
        self.lock = threading.Lock()
        self.snapshot_data = {}
        self.logs = deque(maxlen=60)
        self.path = path or ROOT / 'config/settings.json'
        self.fps = 0
        self.alive = True
        self.publish()

    def submit_event(self, event):
        self.commands.put_nowait(('event', event, None))

    def command(self, name, value=None):
        future = Future()
        self.commands.put_nowait((name, value, future))
        return future

    def save_settings(self):
        atomic_json(self.path, self.world.cfg.model_dump())
        self.publish()

    def execute(self, name, data):
        w = self.world
        if name == 'event':
            return self.router.process(data)
        if name == 'start':
            if w.phase == 'goal':
                w.restart(reset_score=True)
            w.running = True
        elif name == 'pause':
            w.running = False
        elif name == 'restart':
            w.restart(reset_score=bool(data))
            self.router.effects.clear()
        elif name == 'settings':
            new = Settings.model_validate(data).checked()
            old = w.cfg
            atomic_json(self.path, new.model_dump())
            w.cfg = new
            if (new.columns, new.rows) != (old.columns, old.rows):
                w.restart()
            if not new.allow_negative:
                w.wins = max(0, w.wins)
        else:
            raise ValueError('Comando desconhecido.')
        return {'ok': True}

    def process_commands(self):
        for _ in range(128):
            try:
                name, data, f = self.commands.get_nowait()
            except queue.Empty:
                break
            try:
                result = self.execute(name, data)
                self.publish()
                if f and not f.cancelled():
                    f.set_result(result)
            except Exception as exc:
                self.logs.append(f'{time.strftime("%H:%M:%S")} · Falha: {type(exc).__name__}')
                if f and not f.cancelled():
                    f.set_exception(exc)

    def publish(self):
        state = self.world.snapshot()
        state.update(
            fps=round(self.fps, 1),
            queue=self.commands.qsize(),
            config=self.world.cfg.model_dump(),
            catalog=list(self.router.catalog.values()),
            notice=self.router.notice,
            logs=list(self.logs)
        )
        with self.lock:
            self.snapshot_data = state

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.snapshot_data)
