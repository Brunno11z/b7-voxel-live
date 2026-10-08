"""Single process, main-thread pygame, isolated async backend/network thread."""
import os, sys, socket, threading, time, webbrowser, argparse
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from configuration import load_settings
from runtime import Runtime

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--no-browser', action='store_true')
    p.add_argument('--headless', action='store_true')
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--screenshot')
    p.add_argument('--demo', action='store_true')
    args = p.parse_args()

    if args.headless:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'

    # Bind before creating the game: the port is also the single-instance lock.
    sock = socket.socket()
    if os.name == 'nt':
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind(('127.0.0.1', 5000))
        sock.listen(128)
    except OSError:
        print('Já existe um programa na porta 5000. Reutilize o painel ou feche o programa anterior.')
        if not args.no_browser:
            webbrowser.open('http://127.0.0.1:5000')
        return 1

    import pygame as pg, uvicorn
    from game.render import Renderer
    from panel.server import make_app

    try:
        runtime = Runtime(load_settings())
    except Exception as exc:
        print('Configuração inválida. Corrija ou renomeie config/settings.json. Erro:', type(exc).__name__)
        sock.close()
        return 1

    renderer = Renderer(runtime.world)
    server = uvicorn.Server(uvicorn.Config(make_app(runtime), host='127.0.0.1', port=5000, log_level='warning', access_log=False))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()

    if not args.no_browser:
        def open_panel():
            for _ in range(100):
                if server.started:
                    webbrowser.open('http://127.0.0.1:5000')
                    return
                time.sleep(0.05)
        threading.Thread(target=open_panel, daemon=True).start()

    if args.demo:
        runtime.world.running = True
        runtime.world.add(205)

    clock = pg.time.Clock()
    frames = 0
    accumulator = 0.0

    try:
        while runtime.alive:
            dt = min(clock.tick(60) / 1000.0, 0.1)
            frames += 1
            accumulator += dt

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    runtime.alive = False
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        runtime.alive = False
                    elif event.key == pg.K_SPACE:
                        runtime.world.running = not runtime.world.running
                    elif event.key == pg.K_m:
                        # Quick toggle between auto and manual control mode
                        runtime.world.cfg.control_mode = 'manual' if runtime.world.cfg.control_mode == 'auto' else 'auto'
                        runtime.save_settings()

            # Poll keyboard state for fluid manual control
            keys = pg.key.get_pressed()

            runtime.process_commands()
            while accumulator >= 1 / 120:
                runtime.world.tick(1 / 120)
                renderer.tick(1 / 120, runtime.router, keys=keys)
                accumulator -= 1 / 120

            renderer.draw()
            runtime.fps = clock.get_fps()
            if frames % 12 == 0:
                runtime.publish()
            if args.frames and frames >= args.frames:
                break
        if args.screenshot:
            pg.image.save(renderer.canvas, args.screenshot)
    finally:
        server.should_exit = True
        thread.join(timeout=6)
        renderer.close()
        sock.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
