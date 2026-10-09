import pygame as pg
from game.model import World
from game.actor import Explorer
from configuration import Settings

class FakeKeys:
    def __init__(self, pressed):
        self.pressed = set(pressed)
    def __getitem__(self, item):
        return item in self.pressed

def test_manual_mode_keyboard_controls_left_right_jump():
    cfg = Settings(control_mode='manual')
    w = World(cfg)
    hero = Explorer(w)
    w.hero = hero

    # Right arrow
    keys_right = FakeKeys([pg.K_RIGHT])
    hero.tick(1/60, keys=keys_right)
    assert hero.vx > 0, "Character should move right on K_RIGHT"

    # Jump with Space
    hero.grounded = True
    keys_jump = FakeKeys([pg.K_SPACE])
    hero.tick(1/60, keys=keys_jump)
    assert hero.vy < 0, "Character should jump on K_SPACE"

def test_pause_key_mapped():
    # Make sure main event loop matches K_p
    content = open('/tmp/project/main.py').read()
    assert 'event.key == pg.K_p:' in content
    assert 'runtime.world.running = not runtime.world.running' in content
