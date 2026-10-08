import pytest
import pygame as pg
from pathlib import Path
from configuration import Settings, ACTIONS
from game.model import World
from game.actor import Explorer
from game.voxel_character import VoxelCharacter, SKINS_METADATA
from game.render import Renderer

def test_settings_skins_and_control():
    s = Settings()
    assert s.control_mode == 'auto'
    assert s.skin_preset == 'rei_coroa'
    assert s.show_barriers is True
    assert s.show_supporter_avatar is True
    assert s.show_thought_bubble is True
    assert s.show_thought_bubble_manual is False
    
    # Update to another zip skin
    s.skin_preset = 'pato_dourado'
    s.control_mode = 'manual'
    s_dict = s.model_dump()
    assert s_dict['skin_preset'] == 'pato_dourado'
    assert s_dict['control_mode'] == 'manual'
    assert s_dict['show_supporter_avatar'] is True

def test_voxel_character_skins_and_held_blocks():
    char = VoxelCharacter()
    for preset in ['rei_coroa', 'pato_dourado', 'aesthetic_boy', 'guerreiro_voxel']:
        char.set_skin(preset)
        assert char.skin_name == preset
        for mat in [0, 1, 2]:
            surf = char.frame('walk', 0, 1, held_material=mat)
            assert isinstance(surf, pg.Surface)
            assert surf.get_width() > 0 and surf.get_height() > 0
            
            # Idle and build frames
            surf_idle = char.frame('idle', 0, -1, held_material=mat)
            assert surf_idle.get_width() > 0
            surf_build = char.frame('build', 0, 1, held_material=mat)
            assert surf_build.get_width() > 0

def test_actor_manual_control_and_material_tracking():
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
    
    # In manual mode, moving right advances and places blocks
    assert hero.box.x > init_x + 20
    assert len(w.blocks) >= initial_blocks
    assert hasattr(hero, 'current_material')

def test_all_25d_icons_and_gift_exist():
    assets_dir = Path(__file__).resolve().parents[1] / 'assets'
    assert (assets_dir / 'gift.png').exists()
    for a in ACTIONS:
        icon_path = assets_dir / f'icon_{a}.png'
        assert icon_path.exists(), f'Missing {icon_path}'
        im = pg.image.load(str(icon_path))
        assert im.get_width() >= 48 and im.get_height() >= 48

def test_renderer_with_barriers_supporter_avatar_and_bubbles():
    w = World(Settings(control_mode='manual', show_thought_bubble_manual=False))
    r = Renderer(w)
    
    # Tick and draw fixed barriers
    r.tick(1/60, type('Router', (), {'catalog': {}, 'effects': []})())
    r.draw_fixed_barriers()
    
    # In manual mode with show_thought_bubble_manual=False, bubble should be suppressed
    r.hero_bubble = {'action': 'TORNADO', 'start': r.time}
    r.draw_hero_bubble()
    assert r.hero_bubble is None
    
    # Test supporter avatar toast notification
    r.toasts.append({"name": "Bruno", "action": "TORNADO", "count": 1, "avatar": "https://example.com/avatar.jpg", "time": r.time})
    assert len(r.toasts) == 1
    
    # HUD should draw square action cards
    r.hud()
    assert r.canvas.get_width() == 720
    assert r.canvas.get_height() == 1280
    r.close()

