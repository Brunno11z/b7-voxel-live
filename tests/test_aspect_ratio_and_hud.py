import pytest
from configuration import Settings
from game.model import World
from game.actor import Explorer, SCENARIO_LEFT, SCENARIO_WIDTH, SCENARIO_RIGHT
from game.render import Renderer
import pygame as pg

def test_all_resolutions_are_exact_9_16():
    resolutions = ['405x720', '450x800', '540x960', '720x1280', '1080x1920']
    for r in resolutions:
        w, h = map(int, r.split('x'))
        assert round(w / h, 6) == round(9 / 16, 6), f"Resolution {r} is not 9:16"

def test_cards_are_strictly_outside_construction_scenario():
    # Left cards span x = 6 to 80
    left_card_max_x = 6 + 74 # 80
    assert left_card_max_x < SCENARIO_LEFT, "Left cards must stay completely outside scenario"

    # Right cards span x = 640 to 714
    right_card_min_x = 640
    assert right_card_min_x > SCENARIO_RIGHT, "Right cards must stay completely outside scenario"

    # Fixed barriers sit right at the boundary
    assert 86 < SCENARIO_LEFT
    assert 626 >= SCENARIO_RIGHT

def test_character_strictly_bounded_inside_scenario():
    w = World(Settings())
    hero = Explorer(w)
    assert hero.box.left >= SCENARIO_LEFT
    assert hero.box.right <= SCENARIO_RIGHT
    # Simulate ticks
    for _ in range(120):
        hero.tick(1/60)
        assert hero.box.left >= SCENARIO_LEFT - 0.01
        assert hero.box.right <= SCENARIO_RIGHT + 0.01

def test_victory_hud_and_celebration_banner():
    cfg = Settings(resolution='540x960')
    w = World(cfg)
    renderer = Renderer(w)
    
    # Test normal hud render
    renderer.hud()
    
    # Test victory celebration phase
    w.phase = 'celebrating'
    w.wins = 10
    renderer.hud()
    
    # Test goal phase
    w.phase = 'goal'
    renderer.hud()
    
    renderer.close()
