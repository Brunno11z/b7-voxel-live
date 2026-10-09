import pytest
from configuration import Settings
from game.model import World
from game.render import Renderer

def test_settings_borderless_default_and_cards_scale():
    cfg = Settings()
    assert cfg.borderless is True, "Game should default to borderless mode"
    assert cfg.show_gift_cards is True, "Gift cards should be visible by default"
    assert cfg.gift_cards_scale == 100, "Default gift cards scale should be 100"

def test_renderer_renders_with_cards_hidden_clean_screen():
    cfg = Settings(show_gift_cards=False, resolution='1280x720')
    w = World(cfg)
    r = Renderer(w)
    r.draw()
    assert r.canvas is not None

def test_renderer_renders_with_custom_card_scale():
    for scale in (25, 50, 75, 100):
        cfg = Settings(gift_cards_scale=scale, resolution='1280x720')
        w = World(cfg)
        r = Renderer(w)
        r.draw()
        assert r.canvas is not None

def test_main_event_loop_has_h_key_shortcut():
    with open('/tmp/project/main.py') as f:
        content = f.read()
    assert 'pg.K_h' in content
    assert 'show_gift_cards' in content
