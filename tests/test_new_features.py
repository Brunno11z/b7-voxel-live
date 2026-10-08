import pytest
import pygame as pg
from pathlib import Path
from configuration import Settings, DEFAULT_SKIN_COLORS, ACTIONS
from game.model import World
from game.actor import Explorer
from game.voxel_character import VoxelCharacter
from game.render import Renderer

def test_settings_skins_and_control():
    s = Settings()
    assert s.control_mode == 'auto'
    assert s.skin_preset == 'default'
    assert s.show_barriers is True
    assert 'shirt' in s.skin_colors
    
    # Update to Rock Lee
    s.skin_preset = 'rock_lee'
    s.control_mode = 'manual'
    s_dict = s.model_dump()
    assert s_dict['skin_preset'] == 'rock_lee'
    assert s_dict['control_mode'] == 'manual'

def test_voxel_character_palettes():
    char = VoxelCharacter()
    for preset in ['default', 'rock_lee', 'alex', 'ninja', 'neon', 'zombie', 'custom']:
        char.set_skin(preset, DEFAULT_SKIN_COLORS)
        assert char.skin_preset == preset
        surf = char.frame('walk', 0, 1)
        assert isinstance(surf, pg.Surface)
        assert surf.get_width() > 0 and surf.get_height() > 0

def test_actor_manual_control_and_placement():
    w = World(Settings(control_mode='manual'))
    w.running = True
    hero = Explorer(w)
    hero.box.centerx = 52 + 5 * hero.cell
    hero.box.bottom = 0
    
    initial_blocks = len(w.blocks)
    # Simulate keys pressed (moving right)
    keys = {pg.K_LEFT: 0, pg.K_RIGHT: 1, pg.K_a: 0, pg.K_d: 1, pg.K_UP: 0, pg.K_w: 0, pg.K_SPACE: 0}
    init_x = hero.box.x
    for _ in range(60):
        hero.tick(1/60, keys=keys)
    
    # In manual mode, moving right should advance position and place blocks
    assert hero.box.x > init_x + 20
    assert len(w.blocks) >= initial_blocks

def test_all_25d_icons_and_gift_exist():
    assets_dir = Path(__file__).resolve().parents[1] / 'assets'
    assert (assets_dir / 'gift.png').exists()
    for a in ACTIONS:
        icon_path = assets_dir / f'icon_{a}.png'
        assert icon_path.exists(), f'Missing {icon_path}'
        im = pg.image.load(str(icon_path))
        assert im.get_width() >= 48 and im.get_height() >= 48

def test_renderer_with_barriers_and_bubbles():
    w = World(Settings())
    r = Renderer(w)
    
    # Tick and draw a frame
    r.tick(1/60, type('Router', (), {'catalog': {}, 'effects': []})())
    r.draw_fixed_barriers()
    
    # Trigger hero bubble with action
    r.hero_bubble = {'action': 'TORNADO', 'start': r.time}
    r.draw_hero_bubble()
    
    # Add a tornado effect
    r.effects.append({'action': 'TORNADO', 'start': r.time, 'x': 360, 'y': -200})
    r.draw_effects()
    
    # HUD should draw gift emojis over actions
    r.hud()
    assert r.canvas.get_width() == 720
    assert r.canvas.get_height() == 1280
    r.close()
