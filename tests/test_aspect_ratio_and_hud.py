import pytest
from configuration import Settings
from game.model import World
from game.actor import Explorer, SCENARIO_LEFT, SCENARIO_WIDTH, SCENARIO_RIGHT
from game.render import Renderer
import pygame as pg

def test_default_resolution_is_horizontal_hd():
    cfg = Settings()
    assert cfg.resolution == '1280x720', "Default resolution should be 1280x720 (Horizontal HD)"
    w, h = map(int, cfg.resolution.split('x'))
    assert w > h, "Must open in horizontal mode"

def test_original_scenario_and_barriers_dimensions():
    assert SCENARIO_LEFT == 52
    assert SCENARIO_WIDTH == 616
    assert SCENARIO_RIGHT == 668
    # Left barrier: x=24..52 (width 28)
    # Right barrier: x=668..696 (width 28)
    assert 24 + 28 == SCENARIO_LEFT
    assert 668 == SCENARIO_RIGHT

def test_character_clamped_and_navigates_within_barriers():
    w = World(Settings())
    hero = Explorer(w)
    w.hero = hero
    assert hero.box.left >= SCENARIO_LEFT
    assert hero.box.right <= SCENARIO_RIGHT
    # Simulate ticks
    for _ in range(120):
        hero.tick(1/60)
        assert hero.box.left >= SCENARIO_LEFT - 0.01
        assert hero.box.right <= SCENARIO_RIGHT + 0.01

def test_normal_construction_only_builds_when_walking_or_jumping():
    # Standing still: no blocks placed
    cfg = Settings(control_mode='manual', build_rate=10.0)
    w = World(cfg)
    w.running = True
    hero = Explorer(w)
    w.hero = hero
    
    # Tick 60 times without moving keys
    for _ in range(60):
        w.tick(1/60)
        hero.tick(1/60, keys={})
    assert w.count == 0, "No blocks should be placed while standing still"
    assert w.credit > 0, "Credit should accumulate"
    
    # Walking right: places blocks
    keys = {pg.K_RIGHT: 1, pg.K_d: 1}
    for _ in range(120):
        w.tick(1/60)
        hero.tick(1/60, keys=keys)
    assert w.count > 0, "Blocks should be placed while walking"

def test_auto_mode_builds_while_moving_and_jumping():
    cfg = Settings(control_mode='auto', build_rate=8.0)
    w = World(cfg)
    w.running = True
    hero = Explorer(w)
    w.hero = hero
    
    for _ in range(120):
        w.tick(1/60)
        hero.tick(1/60)
    assert w.count > 0, "Auto mode must place blocks while moving/jumping"

def test_gifts_continue_to_help_normally():
    cfg = Settings(control_mode='auto', build_rate=0.0)
    w = World(cfg)
    w.running = True
    assert w.count == 0
    w.add(16)
    assert w.count == 16, "Gifts must add blocks immediately"

def test_victory_plaque_renders_without_error():
    cfg = Settings(resolution='1280x720')
    w = World(cfg)
    renderer = Renderer(w)
    renderer.hud()
    renderer.draw()
    renderer.close()
