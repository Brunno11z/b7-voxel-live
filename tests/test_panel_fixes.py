import threading, time
from starlette.testclient import TestClient
from configuration import Settings, load_settings
from runtime import Runtime
from panel.server import make_app
from services.secrets import save_key, load_key

def test_panel_fixes_and_features(tmp_path):
    cfg_file = tmp_path / 'settings.json'
    cfg = Settings()
    rt = Runtime(cfg, path=cfg_file)
    stop = threading.Event()
    def run():
        while not stop.is_set():
            rt.process_commands()
            rt.publish()
            time.sleep(0.003)
    thread = threading.Thread(target=run)
    thread.start()

    try:
        app = make_app(rt)
        client = TestClient(app)

        # 1. Session token
        res = client.get('/api/session')
        assert res.status_code == 200
        token = res.json()['token']
        headers = {'x-b7-token': token, 'origin': 'http://127.0.0.1:5000'}

        # 2. Save Euler key
        res = client.post('/api/save-key', json={'key': 'euler_secret_test_123'}, headers=headers)
        assert res.status_code == 200
        assert res.json()['key_saved'] is True
        assert load_key() == 'euler_secret_test_123'

        # State reflects saved key
        res = client.get('/api/state')
        assert res.status_code == 200
        state = res.json()
        assert state['key_saved'] is True
        assert '123' in state['key_preview']

        # 3. Equip skin via settings
        new_cfg = cfg.model_dump()
        new_cfg['skin_preset'] = 'pato_dourado'
        new_cfg['action_badges']['BUILD'] = '🧱'
        new_cfg['action_badges']['WIN'] = '👑'
        new_cfg['mappings'] = [
            {'gift_id': '5655', 'gift_name': 'Rosa', 'action': 'BUILD'},
            {'gift_id': '', 'gift_name': '', 'action': 'BUILD'} # Blank mapping shouldn't crash
        ]
        res = client.post('/api/settings', json=new_cfg, headers=headers)
        assert res.status_code == 200
        assert rt.world.cfg.skin_preset == 'pato_dourado'
        assert rt.world.cfg.action_badges['BUILD'] == '🧱'
        assert rt.world.cfg.action_badges['WIN'] == '👑'

        # 4. Runtime.save_settings method
        rt.world.cfg.control_mode = 'manual'
        rt.save_settings()
        loaded = load_settings(cfg_file)
        assert loaded.control_mode == 'manual'
        assert loaded.skin_preset == 'pato_dourado'
    finally:
        stop.set()
        thread.join()

def test_renderer_action_badges_and_custom_emojis():
    from game.render import Renderer
    from game.model import World
    cfg = Settings()
    cfg.action_badges['BUILD'] = '🧱'
    cfg.action_badges['WIN'] = '👑'
    cfg.action_badges['ZAP'] = '⚡'
    world = World(cfg)
    renderer = Renderer(world)

    # Test badge retrieval for emoji
    badge_build = renderer.get_action_badge('BUILD', cfg)
    assert badge_build is not None
    assert badge_build.get_size() == (28, 28)

    # Test badge retrieval for default
    badge_whale = renderer.get_action_badge('SKY_WHALE', cfg)
    assert badge_whale is not None

    # Test HUD rendering with badges and bigger text does not crash
    renderer.draw()
    renderer.close()
